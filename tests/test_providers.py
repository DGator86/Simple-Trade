from datetime import date

import pandas as pd
import pytest
import responses

from simple_trade.data.providers import (
    AlpacaProvider,
    MassiveProvider,
    ProviderError,
    TradierProvider,
)
from simple_trade.data.schema import BAR_COLUMNS, Timeframe


@responses.activate
def test_massive_follows_next_url():
    base = "https://api.massive.com/v2/aggs/ticker/SPY/range/1/day/2024-01-02/2024-01-03"
    responses.get(
        base,
        json={
            "results": [
                {
                    "t": 1704171600000,
                    "o": 1,
                    "h": 2,
                    "l": 0.5,
                    "c": 1.5,
                    "v": 100,
                    "vw": 1.2,
                    "n": 10,
                }
            ],
            "next_url": "https://api.massive.com/v2/aggs/next?cursor=abc",
        },
    )
    responses.get(
        "https://api.massive.com/v2/aggs/next",
        json={
            "results": [{"t": 1704258000000, "o": 2, "h": 3, "l": 1, "c": 2.5, "v": 200}],
        },
    )
    bars = MassiveProvider("k").bars("spy", Timeframe.DAY1, date(2024, 1, 2), date(2024, 1, 3))
    assert list(bars.columns) == BAR_COLUMNS
    assert len(bars) == 2
    assert bars["symbol"].unique().tolist() == ["SPY"]
    assert bars["timestamp"].iloc[0] == pd.Timestamp("2024-01-02 05:00", tz="UTC")
    assert "apiKey=k" in responses.calls[1].request.url
    assert pd.isna(bars["vwap"].iloc[1])


@responses.activate
def test_alpaca_paginates_and_sends_auth():
    url = "https://data.alpaca.markets/v2/stocks/AAPL/bars"
    responses.get(
        url,
        json={
            "bars": [
                {
                    "t": "2024-01-02T14:30:00Z",
                    "o": 1,
                    "h": 2,
                    "l": 1,
                    "c": 2,
                    "v": 5,
                    "vw": 1.5,
                    "n": 3,
                }
            ],
            "next_page_token": "tok",
        },
    )
    responses.get(
        url,
        json={
            "bars": [
                {
                    "t": "2024-01-02T14:31:00Z",
                    "o": 2,
                    "h": 2,
                    "l": 1,
                    "c": 1,
                    "v": 6,
                    "vw": 1.4,
                    "n": 4,
                }
            ],
            "next_page_token": None,
        },
    )
    bars = AlpacaProvider("id", "secret").bars(
        "AAPL", Timeframe.MIN1, date(2024, 1, 2), date(2024, 1, 2)
    )
    assert len(bars) == 2
    req = responses.calls[1].request
    assert req.headers["APCA-API-KEY-ID"] == "id"
    assert "page_token=tok" in req.url
    assert "timeframe=1Min" in req.url


@responses.activate
def test_tradier_daily_handles_single_object():
    responses.get(
        "https://api.tradier.com/v1/markets/history",
        json={
            "history": {
                "day": {
                    "date": "2024-01-02",
                    "open": 1,
                    "high": 2,
                    "low": 1,
                    "close": 2,
                    "volume": 9,
                }
            },
        },
    )
    bars = TradierProvider("t").bars("SPY", Timeframe.DAY1, date(2024, 1, 2), date(2024, 1, 2))
    assert len(bars) == 1
    assert bars["close"].iloc[0] == 2.0


@responses.activate
def test_tradier_empty_history():
    responses.get("https://api.tradier.com/v1/markets/history", json={"history": None})
    bars = TradierProvider("t").bars("SPY", Timeframe.DAY1, date(2024, 1, 2), date(2024, 1, 2))
    assert bars.empty and list(bars.columns) == BAR_COLUMNS


@responses.activate
def test_tradier_timesales_skips_weekends():
    responses.get(
        "https://api.tradier.com/v1/markets/timesales",
        json={
            "series": {
                "data": [
                    {
                        "time": "2024-01-05T09:30:00",
                        "timestamp": 1704465000,
                        "open": 1,
                        "high": 1,
                        "low": 1,
                        "close": 1,
                        "volume": 1,
                        "vwap": 1,
                        "price": 1,
                    }
                ]
            },
        },
    )
    TradierProvider("t").bars("SPY", Timeframe.MIN1, date(2024, 1, 5), date(2024, 1, 7))
    assert len(responses.calls) == 1  # Fri only


@responses.activate
def test_retries_on_429_then_raises_on_4xx(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    url = "https://api.tradier.com/v1/markets/history"
    responses.get(url, status=429)
    responses.get(url, json={"history": None})
    TradierProvider("t").bars("SPY", Timeframe.DAY1, date(2024, 1, 2), date(2024, 1, 2))
    assert len(responses.calls) == 2

    responses.reset()
    responses.get(url, status=401, body="unauthorized")
    with pytest.raises(ProviderError, match="401"):
        TradierProvider("t").bars("SPY", Timeframe.DAY1, date(2024, 1, 2), date(2024, 1, 2))


def test_from_env_requires_key(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="MASSIVE_API_KEY"):
        MassiveProvider.from_env()
