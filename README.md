# Z1 The strategy comparison

Goal: Compare hundreds of multi asset strategies, correct for how many were tried, find out whats actually left.

## v0: Data layer

44 ETFs, 6 asset class buckets (equity, sectors, fixed income, commodities, real estate, FX)
pulled daily OHLCV + Adj Close from yfinance. (OHLCV = open high low close volume)

`data/pull_yfinance.py` pulls all 44, long format (`date, ticker, field, value`), writes `data/processed/panel_yfinance.parquet` and auto-generates `data/MANIFEST.md`. "manifest checks how much data is actually pulled so i dont have empty entries

`data/pull_stooq.py` is for verification of reliability of yfinance, pulls data from stooq of SPY, TLT and GLD to compare with yfinacne and find out if its reliable

`data/clean.py` takes the raw yfinance pull, checks for duplicate `(date, ticker, field)` rows, checks every ticker against the real NYSE trading calendar, and writes the actual cleaned dataframe: `data/processed/panel.parquet`

## Acceptance test (`notebooks/v0_Reliability_Test.ipynb`)

1. SPY CAGR 2000-2025: 8.03%, matches the well-known 7-8% figure. Pass. (CAGR = cumulative annual growth rate)
2. yfinance vs Stooq daily return correlation, 
SPY/TLT/GLD: GLD 0.999991 (clean pass), SPY 0.998595, TLT 0.997766, pass.
3. Day gaps checked against a real NYSE calendar, all 44 tickers had 0 missing days each. Pass.

Full numbers in `data/MANIFEST.md`.

`clean.py`'s own run confirms 0 duplicates, 0 calendar gaps for all tickers

## v1 will be a backtest "machine"