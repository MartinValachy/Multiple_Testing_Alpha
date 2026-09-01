# Z1 The strategy comparison

Goal: Compare hundreds of multi asset strategies, correct for how many were tried, find out whats actually left.

## v0: Data layer

44 ETFs, 6 asset class buckets (equity, sectors, fixed income, commodities, real estate, FX) pulled daily OHLCV + Adj Close from yfinance. (OHLCV = open high low close volume)

`data/pull_yfinance.py` pulls all 44 tickers in long format (`date, ticker, field, value`), writes `data/processed/panel_yfinance.parquet` and auto-generates `data/MANIFEST.md`. "manifest" checks how much data is actually pulled so i dont have empty entries

`data/pull_stooq.py` is for verification of reliability of yfinance, pulls data from stooq of SPY, TLT and GLD to compare with yfinacne and find out if its reliable

`data/clean.py` takes the raw yfinance pull, checks for duplicate `(date, ticker, field)` rows, checks every ticker against the real NYSE trading calendar, and writes the actual cleaned dataframe: `data/processed/panel.parquet`

## Acceptance test of data (`notebooks/v0_Reliability_Test.ipynb`)

1. SPY CAGR 2000-2025: 8.03%, matches the well-known 7-8% figure. Pass. (CAGR = cumulative annual growth rate)
2. yfinance vs Stooq daily return correlation, 
SPY/TLT/GLD: GLD 0.999991 (clean pass), SPY 0.998595, TLT 0.997766, pass.
3. Day gaps checked against a real NYSE calendar, all 44 tickers had 0 missing days each. Pass.

Full numbers in `data/MANIFEST.md`.

`clean.py` run confirms no duplicates nor calendar gaps for all tickers

## v1: backtest engine 

`engine/signals.py`: 3 primitive signals: 
return over lookback 
vol-scaled return
cross-sectional rank

`engine/sizing.py` : vol targeting (weight = signal * target_vol/realized_vol) and turnover calculation

`engine/costs.py` : Corwin-Schultz spread estimate from daily high/low, "Amihud illiquidity" as a cross-check. Literature-parameterized, not calibrated. Every result using this carries that caveat.

Corwin-Schultz alone overestimates spreads badly for liquid names. For example SPY came out around 27bps, real SPY spread is under 1bp. 
Fixed it with a liquidity ceiling. Each ticker's average dollar volume (`Close * Volume`, already have it) sorts it into a tier (>=$1B/day, >=$100M/day, below that), each tier has a published typical spread ceiling (1.5/4/12bps), Corwin-Schultz gets capped there. 
It keeps the day-to-day shape from Corwin-Schultz, but fixes the absolute level.

`engine/backtest.py` : runs signal -> weight -> turnover -> cost -> daily pnl. 

Design note: 
Weight here is `signal * vol_scalar`, using the raw momentum magnitude, not `sign(signal) * vol_scalar` like the classic academic construction. Different Sharpe than a pure sign-based bet.

## v1 acceptance test (`tests/test_engine.py`)

12-1 month momentum (skip most recent month). Im checking gross returns, not net.

Tickers: SPY, EEM, TLT, HYG, GLD, DBC, VNQ, UUP, one per asset class bucket

I tried two other selections as well:
- original equity heavy set (SPY/QQQ/IWM-tilted): gross Sharpe 0.38
- correlation optimized set (lowest cross-bucket correlation per bucket, picked before looking at any momentum result): gross Sharpe 0.06

This basket lands at 0.43, and is the most defensible.
The spread itself (0.06 to 0.43 across "reasonable" 8-ticker choices) is simply more honest.
No hand picked basket reliably reproduces the literature's 1.0+ Sharpe, which comes from 58 genuinely independent instruments, not 8 like I did).

Portfolio (equal-weighted, gross): Sharpe 0.43, positive.
