"""Alpaca market data API v2 (stocks)."""

from __future__ import annotations

import os
from datetime import date, datetime, time, timezone

import pandas as pd

from simple_trade.data.providers.base import Provider, require_env
from simple_trade.data.schema import Timeframe, empty_bars, normalize_bars

_TIMEFRAME = {
    Timeframe.MIN1: "1Min",
    Timeframe.MIN5: "5Min",
    Timeframe.MIN15: "15Min",
    Timeframe.HOUR1: "1Hour",
    Timeframe.DAY1: "1Day",
}


class AlpacaProvider(Provider):
    name = "alpaca"

    def __init__(self, key_id: str, secret_key: str, feed: str = "iex",
                 base_url: str = "https://data.alpaca.markets", **kwargs):
        super().__init__(**kwargs)
        self.feed = feed
        self.base_url = base_url.rstrip("/")
        self.session.headers.update({"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret_key})

    @classmethod
    def from_env(cls) -> AlpacaProvider:
        return cls(
            require_env("ALPACA_API_KEY_ID"),
            require_env("ALPACA_API_SECRET_KEY"),
            feed=os.environ.get("ALPACA_FEED", "iex"),
        )

    def bars(self, symbol: str, timeframe: Timeframe, start: date, end: date) -> pd.DataFrame:
        url = f"{self.base_url}/v2/stocks/{symbol.upper()}/bars"
        params = {
            "timeframe": _TIMEFRAME[timeframe],
            "start": datetime.combine(start, time.min, timezone.utc).isoformat(),
            "end": datetime.combine(end, time.max, timezone.utc).isoformat(),
            "adjustment": "all",
            "feed": self.feed,
            "limit": 10000,
        }
        rows: list[dict] = []
        while True:
            payload = self._get(url, params=params)
            rows.extend(payload.get("bars") or [])
            token = payload.get("next_page_token")
            if not token:
                break
            params["page_token"] = token
        if not rows:
            return empty_bars()
        df = pd.DataFrame(rows).rename(columns={
            "t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close",
            "v": "volume", "vw": "vwap", "n": "trade_count",
        })
        return normalize_bars(df, symbol, self.name)
