from datetime import date
from itertools import pairwise

import pandas as pd
import responses

from simple_trade.data.cli import _chunks, main
from simple_trade.data.schema import Timeframe, normalize_bars
from simple_trade.data.store import BarStore


def _bars(days, close):
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(days),
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": close,
            "volume": 1,
        }
    )
    return normalize_bars(df, "SPY", "test")


def test_store_merges_and_new_data_wins(tmp_path):
    store = BarStore(tmp_path)
    store.write(_bars(["2024-01-02", "2024-01-03"], 1.0), Timeframe.DAY1)
    store.write(_bars(["2024-01-03", "2024-01-04"], 2.0), Timeframe.DAY1)
    out = store.read("test", Timeframe.DAY1, "SPY")
    assert out["close"].tolist() == [1.0, 2.0, 2.0]


def test_chunks_cover_range_without_overlap():
    parts = list(_chunks(date(2024, 1, 1), date(2024, 3, 1), 30))
    assert parts[0][0] == date(2024, 1, 1) and parts[-1][1] == date(2024, 3, 1)
    for (_, b), (c, _) in pairwise(parts):
        assert (c - b).days == 1


@responses.activate
def test_cli_fetch_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADIER_TOKEN", "t")
    responses.get(
        "https://api.tradier.com/v1/markets/history",
        json={
            "history": {
                "day": [
                    {"date": "2024-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 9}
                ]
            },
        },
    )
    rc = main(
        [
            "fetch",
            "--source",
            "tradier",
            "--symbols",
            "spy",
            "--start",
            "2024-01-02",
            "--end",
            "2024-01-02",
            "--data-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    assert (tmp_path / "bars/tradier/1d/SPY.parquet").exists()


def test_cli_missing_key_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ALPACA_API_KEY_ID", raising=False)
    rc = main(
        [
            "fetch",
            "--source",
            "alpaca",
            "--symbols",
            "SPY",
            "--start",
            "2024-01-02",
            "--data-dir",
            str(tmp_path),
        ]
    )
    assert rc == 1
    assert "ALPACA_API_KEY_ID" in capsys.readouterr().err
