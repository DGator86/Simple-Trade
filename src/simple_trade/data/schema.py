"""Common OHLCV bar schema shared by every provider."""

from __future__ import annotations

from enum import StrEnum

import pandas as pd

BAR_COLUMNS = [
    "symbol",
    "timestamp",  # bar open time, tz-aware UTC
    "open",
    "high",
    "low",
    "close",
    "volume",
    "vwap",
    "trade_count",
    "source",
]


class Timeframe(StrEnum):
    MIN1 = "1m"
    MIN5 = "5m"
    MIN15 = "15m"
    HOUR1 = "1h"
    DAY1 = "1d"

    @property
    def is_intraday(self) -> bool:
        return self is not Timeframe.DAY1


def normalize_bars(df: pd.DataFrame, symbol: str, source: str) -> pd.DataFrame:
    """Coerce a provider frame into BAR_COLUMNS order, dtypes and sort."""
    out = df.copy()
    out["symbol"] = symbol.upper()
    out["source"] = source
    for col in ("vwap", "trade_count"):
        if col not in out:
            out[col] = pd.NA
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    for col in ("open", "high", "low", "close", "vwap"):
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
    for col in ("volume", "trade_count"):
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("Float64")
    out = out[BAR_COLUMNS].sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    return out.reset_index(drop=True)


def empty_bars() -> pd.DataFrame:
    return normalize_bars(
        pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"]), "", ""
    )
