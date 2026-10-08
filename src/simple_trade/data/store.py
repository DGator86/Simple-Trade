"""Parquet store: one file per (source, timeframe, symbol), merged on write."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from simple_trade.data.schema import BAR_COLUMNS, Timeframe


class BarStore:
    def __init__(self, root: str | os.PathLike | None = None):
        self.root = Path(root or os.environ.get("SIMPLE_TRADE_DATA_DIR", "data"))

    def path(self, source: str, timeframe: Timeframe, symbol: str) -> Path:
        return self.root / "bars" / source / timeframe.value / f"{symbol.upper()}.parquet"

    def read(self, source: str, timeframe: Timeframe, symbol: str) -> pd.DataFrame:
        p = self.path(source, timeframe, symbol)
        if not p.exists():
            return pd.DataFrame(columns=BAR_COLUMNS)
        return pd.read_parquet(p)

    def write(self, bars: pd.DataFrame, timeframe: Timeframe) -> list[Path]:
        """Merge bars into existing files, deduplicating on timestamp (new data wins)."""
        written = []
        for (source, symbol), group in bars.groupby(["source", "symbol"]):
            p = self.path(source, timeframe, symbol)
            p.parent.mkdir(parents=True, exist_ok=True)
            existing = self.read(source, timeframe, symbol)
            merged = group if existing.empty else pd.concat([existing, group])
            merged = (
                merged.sort_values("timestamp")
                .drop_duplicates("timestamp", keep="last")
                .reset_index(drop=True)
            )
            merged.to_parquet(p, index=False)
            written.append(p)
        return written
