"""Tradier market data: /markets/history (daily) and /markets/timesales (intraday).

Tradier only keeps about 20 trading days of 1m timesales (40 for 5m/15m), so it is
best used for daily history and recent intraday top-ups.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd

from simple_trade.data.providers.base import Provider, ProviderError, require_env
from simple_trade.data.schema import Timeframe, empty_bars, normalize_bars

_INTRADAY = {Timeframe.MIN1: "1min", Timeframe.MIN5: "5min", Timeframe.MIN15: "15min"}


def _as_list(value) -> list[dict]:
    """Tradier returns a bare object instead of a one-element list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class TradierProvider(Provider):
    name = "tradier"

    def __init__(self, token: str, base_url: str = "https://api.tradier.com", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        )

    @classmethod
    def from_env(cls) -> TradierProvider:
        sandbox = os.environ.get("TRADIER_ENV", "").lower() == "sandbox"
        base = "https://sandbox.tradier.com" if sandbox else "https://api.tradier.com"
        return cls(require_env("TRADIER_TOKEN"), base_url=base)

    def bars(self, symbol: str, timeframe: Timeframe, start: date, end: date) -> pd.DataFrame:
        if timeframe is Timeframe.DAY1:
            return self._daily(symbol, start, end)
        if timeframe in _INTRADAY:
            return self._timesales(symbol, timeframe, start, end)
        raise ProviderError(f"tradier does not support timeframe {timeframe.value}")

    def _daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        payload = self._get(f"{self.base_url}/v1/markets/history", params={
            "symbol": symbol.upper(), "interval": "daily",
            "start": start.isoformat(), "end": end.isoformat(),
        })
        rows = _as_list((payload.get("history") or {}).get("day"))
        if not rows:
            return empty_bars()
        df = pd.DataFrame(rows).rename(columns={"date": "timestamp"})
        return normalize_bars(df, symbol, self.name)

    def _timesales(self, symbol: str, timeframe: Timeframe, start: date, end: date):
        # Query day by day: Tradier caps timesales responses per request.
        frames = []
        day = start
        while day <= end:
            if day.weekday() < 5:
                payload = self._get(f"{self.base_url}/v1/markets/timesales", params={
                    "symbol": symbol.upper(), "interval": _INTRADAY[timeframe],
                    "start": f"{day.isoformat()} 00:00", "end": f"{day.isoformat()} 23:59",
                    "session_filter": "all",
                })
                rows = _as_list((payload.get("series") or {}).get("data"))
                if rows:
                    frames.append(pd.DataFrame(rows))
            day += timedelta(days=1)
        if not frames:
            return empty_bars()
        df = pd.concat(frames)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        return normalize_bars(df, symbol, self.name)
