"""Fetch bars from a provider into the local Parquet store.

    simple-trade-data fetch --source massive --symbols SPY,QQQ --timeframe 1d \
        --start 2015-01-01 --end 2025-12-31
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import pandas as pd

from simple_trade.data.providers import PROVIDERS, ProviderError
from simple_trade.data.schema import Timeframe
from simple_trade.data.store import BarStore

# Request window per call, sized to stay well under provider page limits.
_CHUNK_DAYS = {Timeframe.DAY1: 3650, Timeframe.HOUR1: 365}
_DEFAULT_CHUNK_DAYS = 30


def _chunks(start: date, end: date, days: int):
    while start <= end:
        stop = min(end, start + timedelta(days=days - 1))
        yield start, stop
        start = stop + timedelta(days=1)


def fetch(source: str, symbols: list[str], timeframe: Timeframe, start: date, end: date,
          store: BarStore) -> int:
    provider = PROVIDERS[source].from_env()
    total = 0
    for symbol in symbols:
        frames = [
            provider.bars(symbol, timeframe, a, b)
            for a, b in _chunks(start, end, _CHUNK_DAYS.get(timeframe, _DEFAULT_CHUNK_DAYS))
        ]
        frames = [f for f in frames if not f.empty]
        if not frames:
            print(f"{source} {symbol} {timeframe.value}: no data", file=sys.stderr)
            continue
        bars = pd.concat(frames)
        paths = store.write(bars, timeframe)
        total += len(bars)
        print(f"{source} {symbol} {timeframe.value}: {len(bars)} bars -> {paths[0]}")
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="simple-trade-data")
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch", help="download bars into the Parquet store")
    f.add_argument("--source", choices=sorted(PROVIDERS), required=True)
    f.add_argument("--symbols", required=True, help="comma-separated tickers")
    f.add_argument("--timeframe", choices=[t.value for t in Timeframe], default="1d")
    f.add_argument("--start", type=date.fromisoformat, required=True)
    f.add_argument("--end", type=date.fromisoformat, default=date.today())
    f.add_argument("--data-dir", default=None)
    args = parser.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    try:
        fetch(args.source, symbols, Timeframe(args.timeframe), args.start, args.end,
              BarStore(args.data_dir))
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
