"""Massive (formerly Polygon.io) aggregates API."""

from __future__ import annotations

import os
from datetime import date

import pandas as pd

from simple_trade.data.providers.base import Provider, require_env
from simple_trade.data.schema import Timeframe, empty_bars, normalize_bars

_TIMESPAN = {
    Timeframe.MIN1: (1, "minute"),
    Timeframe.MIN5: (5, "minute"),
    Timeframe.MIN15: (15, "minute"),
    Timeframe.HOUR1: (1, "hour"),
    Timeframe.DAY1: (1, "day"),
}


class MassiveProvider(Provider):
    name = "massive"

    def __init__(self, api_key: str, base_url: str = "https://api.massive.com", **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_env(cls) -> MassiveProvider:
        return cls(
            require_env("MASSIVE_API_KEY"),
            base_url=os.environ.get("MASSIVE_BASE_URL", "https://api.massive.com"),
        )

    def bars(self, symbol: str, timeframe: Timeframe, start: date, end: date) -> pd.DataFrame:
        mult, span = _TIMESPAN[timeframe]
        url = (
            f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/range/{mult}/{span}/"
            f"{start.isoformat()}/{end.isoformat()}"
        )
        params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self.api_key}
        rows: list[dict] = []
        while url:
            payload = self._get(url, params=params)
            rows.extend(payload.get("results") or [])
            url = payload.get("next_url")
            # next_url already carries the query except the key
            params = {"apiKey": self.api_key}
        if not rows:
            return empty_bars()
        df = pd.DataFrame(rows).rename(
            columns={
                "t": "timestamp",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
                "vw": "vwap",
                "n": "trade_count",
            }
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return normalize_bars(df, symbol, self.name)
