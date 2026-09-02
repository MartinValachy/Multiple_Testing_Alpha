# Z1: the strategy zoo

Enumerate a ca 800 multi-asset strategies, write the list down before running anything, then find out how many are still alive once you correct for the fact that you tried all of them.

Short answer: none of them.

Data is 44 ETFs across 6 buckets (equity, sectors, fixed income, commodities, real estate, FX), daily OHLCV (open high low close volume) from yfinance, longest available history per ticker.

## How to run

```bash
pip install -r requirements.txt
python data/pull_yfinance.py     # writes data/processed/panel_yfinance.parquet + MANIFEST.md
python data/clean.py             # writes data/processed/panel.parquet
pytest tests/test_engine.py -s   # v1 acceptance test
python zoo/grid.py               # prints the config count, runs nothing
python zoo/run_grid.py           # all 780 configs -> results/zoo_raw_stats.parquet
python stats/run_v3.py           # DSR + HLZ + Reality Check
python stats/plot_v3.py          # -> results/v3_sharpe_vs_null.png
```

## v0: data layer

`data/pull_yfinance.py` pulls all 44 tickers in long format (`date, ticker, field, value`) and auto-generates `data/MANIFEST.md`. The manifest is there so I can see how much data actually came back per ticker instead of trusting the pull silently.

`data/pull_stooq.py` pulls SPY, TLT and GLD from a second source, only to check whether yfinance is reliable enough to build on.

`data/clean.py` takes the raw pull, checks for duplicate `(date, ticker, field)` rows, checks every ticker against a real NYSE trading calendar, and writes a clean `data/processed/panel.parquet`.

**Acceptance test** (`notebooks/v0_Reliability_Test.ipynb`):

1. SPY CAGR 2000-2025 is 8.03%, which matches the well known 7-8% figure. Pass. (CAGR = Cumulative Annualized Gross Returns)
2. yfinance vs Stooq daily return correlation: GLD 0.999991, SPY 0.998595, TLT 0.997766. Pass.
3. Day gaps against a real NYSE calendar: all 44 tickers, 0 missing days each. Pass.

## v1: backtest engine

`engine/signals.py`: return over lookback, vol-scaled return, cross-sectional rank.

`engine/sizing.py`: vol targeting (`weight = signal * target_vol / realized_vol`), equal weight, turnover, holding period.

`engine/costs.py`: Corwin-Schultz spread from daily high/low, Amihud illiquidity as a cross-check. 
    **Literature-parameterized, not calibrated to real spread data.** Every number in this repo that takes into account costs has to be taken with discretion because of this

Corwin-Schultz overestimates spreads badly for liquid tickers. SPY came out at roughly 27bps when the real spread is under 1bp. 
I fixed it with a liquidity ceiling: each ticker's average dollar volume sorts it into a tier (>=$1B/day, >=$100M/day, below), each tier has a published typical spread ceiling (1.5 / 4 / 12 bps), and Corwin-Schultz gets capped there. 
It keeps the day-to-day shape and fixes the absolute level.

`engine/backtest.py`: signal -> weight -> turnover -> cost -> daily pnl.

Design note: weight is `signal * vol_scalar`, so the raw momentum magnitude, not `sign(signal) * vol_scalar` like the classic academic construction. That gives a different Sharpe than a pure sign based bet.

**Acceptance test** (`tests/test_engine.py`): 12-1 month momentum, one ticker per bucket (SPY, EEM, TLT, HYG, GLD, DBC, VNQ, UUP), gross returns. Equal-weighted portfolio Sharpe 0.43, positive.

The difference from literature 1.0+ sharpe is that the literature used 50+ uncorrelated tickers and i used only 8

## v2: the zoo

`zoo/grid.py` enumerates the grid before any backtest runs. 780 configs: 4 signal families (tsmom, cross-sectional momentum, short-term reversal, vol-of-vol) x lookback x skip-month variant x 5 holding periods x 3 universe subsets x 2 sizing rules.

**Committed at `01e84db`, before `run_grid.py` was ever executed.** That commit is the pre-registration proof cited in v3. More trials would raise the bar in the v3 correction, not lower it, so there was no incentive to pad the count.

The engine needed 5 additions before it could run the grid: 
`apply_backtest` split out of `run_backtest` so every family reuses the same shift/cost/pnl path, reversal (flips the signal)
vol-of-vol (signal built from a realized vol series)
`run_cross_sectional_backtest` (ranks the universe against itself daily)
`apply_holding_period` (freezes weights between rebalances)
`equal_weight` sizing

`zoo/run_grid.py` runs all 780 and writes `results/zoo_raw_stats.parquet` plus a histogram

Gross Sharpe across all 780: mean 0.20, std 0.19, max 0.67, min -0.46.

## v3: false discovery control

I predicted before running this that nothing would survive, because a max of 0.67 out of 780 tries isnt really a big number. It didn't survive.

`stats/dsr.py`: Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014). The expected maximum Sharpe across N trials grows with N even when no strategy has real skill, so the best observed Sharpe gets judged against that inflated benchmark instead of against zero. The PSR step also corrects for the winner's own skew and kurtosis.

`stats/hlz_haircut.py`: Harvey-Liu-Zhu (2016) haircuts. Bonferroni, Holm, and Benjamini-Hochberg-Yekutieli. BHY is the one that matters here, since it stays valid under arbitrary dependence and these 780 trials are heavily correlated with each other.

`stats/reality_check.py`: White's Reality Check through a stationary bootstrap (Politis & Romano 1994). Random-length blocks, and the same resampled date sequence applied to every trial at once, so both the autocorrelation in daily returns and the cross-trial correlation survive the resampling.

**Result.** Best config was 445 (cross-sectional momentum, 252d lookback, semiannual holding, all 44 tickers, vol targeted) at 0.67 annualized gross Sharpe.

| Test | Result |
|---|---|
| Deflated Sharpe Ratio | 0.639 |
| Uncorrected survivors at 5% | 213 of 780 |
| Bonferroni | 0 |
| Holm | 0 |
| Benjamini-Hochberg-Yekutieli | 0 |
| Reality Check p-value | 0.190 |

213 of 780 configs look significant if you ignore the fact that you ran 780 of them. 
Zero survive once you don't. 

`stats/plot_v3.py` draws the one figure that shows this (`results/v3_sharpe_vs_null.png`): if no config in the grid had any skill at all, the best of 780 tries would still be expected to land at 0.61 annualized. I got 0.67, the entire edge of the winning config is 0.06 Sharpe over what 780 coinflips hand you for free.

The DSR of 0.639 is well under the 0.95 you would want, and the Reality Check p-value of 0.190 says the best-of-780 result is consistent with luck.

Full write-up in `report/v3_false_discovery.md`.

## Conclusion about this project

It's an audit trail showing that a plausible looking 0.67 Sharpe, found across 780 tries on 44 ETFs, is what multiple testing produces on its own. 
The pre-registration commit is what makes that claim checkable rather than something I just assert.

Costs everywhere are literature-parameterized, not calibrated. Treat the magnitudes as directional.