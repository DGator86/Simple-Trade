# Simple-Trade

A simple trading research project. The first piece is market data ingestion from
Massive (formerly Polygon.io), Alpaca and Tradier into a local Parquet store.

## Getting started

```bash
git clone https://github.com/DGator86/Simple-Trade.git
cd Simple-Trade
pip install -e ".[dev]"
cp .env.example .env   # fill in your keys, then export them
```

## Market data

Every provider returns bars in one schema: `symbol, timestamp (UTC bar open), open, high,
low, close, volume, vwap, trade_count, source`. Bars are written to
`data/bars/<source>/<timeframe>/<SYMBOL>.parquet` and merged on re-fetch, so you can top up
a range without duplicating rows.

```bash
simple-trade-data fetch --source massive --symbols SPY,QQQ,IWM --timeframe 1d --start 2004-01-01
simple-trade-data fetch --source alpaca  --symbols SPY --timeframe 1m --start 2020-01-01
simple-trade-data fetch --source tradier --symbols SPY --timeframe 1d --start 2000-01-01
```

| Source  | Env vars                                       | Timeframes          | Notes |
|---------|------------------------------------------------|---------------------|-------|
| massive | `MASSIVE_API_KEY`                              | 1m 5m 15m 1h 1d     | Split-adjusted; history depth depends on plan |
| alpaca  | `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`, `ALPACA_FEED` | 1m 5m 15m 1h 1d | Split- and dividend-adjusted; from 2016; `iex` feed is free, `sip` is paid |
| tradier | `TRADIER_TOKEN`, `TRADIER_ENV`                 | 1m 5m 15m 1d        | Daily goes back decades; intraday only ~20-40 days |

```python
from simple_trade.data import BarStore, Timeframe
spy = BarStore().read("massive", Timeframe.DAY1, "SPY")
```

## License

[MIT](LICENSE)
