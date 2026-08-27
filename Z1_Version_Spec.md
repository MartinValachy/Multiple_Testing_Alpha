---
title: Z1 — The Strategy Zoo — Version Specification
updated: 2026-08-27
status: post-Bloomberg revision (free-data only)
---

# Z1 — The Strategy Zoo: Full Version Specification

**One-line pitch:** enumerate a large, honestly pre-registered space of multi-asset systematic strategies, then find out — with real statistics, not eyeballing — how many of them are still alive after correcting for the fact that you tried all of them. Ship the constructive residue as a sized portfolio.

**Direct answer to "what's the deliverable of v5":** a portfolio built *only* from the strategies that survived v3's false-discovery correction and v4's out-of-sample generalization test, reported as an out-of-sample equity curve with a **bootstrapped confidence interval on its Sharpe ratio** (not a point estimate), a capacity curve showing roughly where that Sharpe decays to zero as size increases, and a comparison against a 60/40 benchmark. The finding isn't "I found alpha" — it's "here is a live, sized portfolio, and here are the honest statistical bounds on whether it's real." Full detail in §2.6.

---

## 0. What changed since the original spec (27 Aug 2026)

Bloomberg access was lost before any futures/intraday data was pulled. This version supersedes the Bloomberg-dependent design in three concrete ways:

1. **Universe is ETF-only.** The 44-ticker panel originally specified for Bloomberg's P3 pull (equity, sector, fixed income, commodity, real-estate, FX ETFs) is reused verbatim — same tickers, same categories — sourced from **yfinance** (primary) with **Stooq** as a secondary cross-check, instead of Bloomberg. See §1.
2. **Carry is dropped as a signal family.** Term-structure carry needs a futures curve. No free source for that is reliable enough to build a real signal on (Quandl's free continuous-futures set is frozen, Stooq's futures coverage is patchy). Faking it with a weak proxy would undermine the entire point of the project. If you open an IBKR account (even paper trading gives free historical futures data), carry can be added later as an appendix — noted as future work, not attempted here.
3. **The C1 cost model is gone; a lightweight substitute is folded into v1.** C1 (calibrate costs on intraday, validate on 20yr bid/ask) doesn't exist without Bloomberg. Z1's backtest engine instead uses a **literature-parameterized** cost proxy (Corwin–Schultz / Amihud, using published coefficient ranges rather than an empirically fit one) — computable from daily OHLCV alone. This is explicitly *not* calibrated to real spread data, and every deliverable that touches costs says so. That caveat is itself good research hygiene, not a weakness to hide.

Everything else — the enumeration-before-looking discipline, DSR/HLZ/Reality Check in v3, CPCV/PBO in v4, the survivor ensemble in v5 — is unchanged, because none of it was ever data-vendor-specific. That was the right bet regardless of what happened to Bloomberg access.

---

## 1. Data universe (final)

**Source:** yfinance (`yf.download` / `Ticker.history`), daily OHLCV + dividend-adjusted close. Stooq as a cross-check on a handful of tickers before trusting yfinance for the full run (yfinance occasionally has adjustment bugs around split/dividend dates — check at least SPY, TLT, GLD against a second source before building anything on top).

| Category | Tickers |
|---|---|
| Equity | SPY QQQ IWM MDY EFA EEM VGK EWJ EWZ EWY EWA EWC EWG EWU EWH VT |
| Sectors | XLB XLE XLF XLI XLK XLP XLU XLV XLY |
| Fixed income | TLT IEF SHY LQD HYG TIP AGG EMB BNDX |
| Commodities | GLD SLV DBC USO DBA PDBC |
| Real estate | VNQ IYR |
| FX | UUP FXE |

44 tickers, 6 asset-class buckets. History varies by inception (SPY since 1993, most sector SPDRs since 1998–2000, EM/frontier ETFs later — this unevenness is itself something v0 must document, not paper over).

**Fields kept per ticker:** `Open, High, Low, Close, Adj Close, Volume`. `Adj Close` (dividend- and split-adjusted) is the total-return proxy — the free-data equivalent of Bloomberg's `TOT_RETURN_INDEX_GROSS_DVDS`. Fund AUM (`FUND_TOTAL_ASSETS`) has no reliable free equivalent — drop it; it was a "nice to have" for capacity sizing, not load-bearing.

---

## 2. Version checkpoints

Each entry: goal, what gets built, the deliverable artifact, the acceptance test that proves it's actually correct (not just "runs without error"), and standalone-shippability.

### 2.0 — v0: Data layer *(~3 days)*

**Goal.** A clean, documented, reproducible price panel — the foundation everything else stands on. Unglamorous on purpose; rushing this corrupts every downstream result.

**Builds:**
- `data/pull_yfinance.py` — pulls all 44 tickers, longest available history, writes long-format parquet (`date, ticker, field, value`), same hygiene discipline as the original BBG spec (manifest, sanity checks, row counts, date-range logging).
- `data/pull_stooq.py` — same universe, secondary source, used only for cross-validation in the acceptance test below.
- `data/clean.py` — alignment (common trading calendar), gap detection, duplicate-timestamp handling, explicit handling of each ETF's actual inception date (no synthetic backfilling before a fund existed).
- `data/MANIFEST.md` — auto-generated, same pattern as the BBG guide: per-ticker row count, date span, % NaN, source.

**Deliverable:** `data/processed/panel.parquet` — the single clean price panel every later version reads from. Plus `data/MANIFEST.md`.

**Acceptance test (must pass before v1 starts):**
1. SPY's adjusted-close CAGR over 2000–2025 matches its well-known published long-run figure (~7–8% nominal) within a percentage point.
2. yfinance vs. Stooq agree on SPY, TLT, and GLD daily returns to within a small tolerance (e.g., correlation > 0.999, mean absolute daily-return difference near zero) over an overlapping window.
3. No ticker has more than a handful of unexplained gap days outside known market holidays.

**Standalone claim if the sprint stopped here:** none — this is infrastructure, not shippable as research.

---

### 2.1 — v1: Backtest engine *(~2.5 days)*

**Goal.** A correct, reusable harness: signal in, position in, cost-aware PnL out. This is what every one of the hundreds of Zoo configurations in v2 will run through, so a bug here is a bug in every result downstream — correctness matters more than sophistication.

**Builds:**
- `engine/signals.py` — signal primitives (return over lookback, vol-scaled return, cross-sectional rank).
- `engine/sizing.py` — volatility targeting (positions scaled to a target annualized vol using a rolling realized-vol estimate), turnover accounting.
- `engine/costs.py` — the literature-parameterized cost proxy:
  - Corwin–Schultz high-low spread estimator (needs only daily high/low):
    $$ \hat{S} = \frac{2(e^{\alpha}-1)}{1+e^{\alpha}}, \quad \alpha = \frac{\sqrt{2\beta}-\sqrt{\beta}}{3-2\sqrt2} - \sqrt{\frac{\gamma}{3-2\sqrt2}} $$
    ($\beta,\gamma$ built from two-day and single-day high-low ranges — full derivation in Corwin & Schultz (2012), your Day-X reading).
  - Amihud illiquidity as a cross-check: $ILLIQ = \frac{1}{T}\sum |r_t| / \text{DollarVolume}_t$.
  - Apply published typical spread ranges for liquid ETFs (a few bps) rather than fitting a coefficient — **every report table using this cost model carries a footnote: "cost estimate is literature-parameterized, not empirically calibrated; treat magnitudes as directional."**
- `engine/backtest.py` — the actual loop: signal → target weights → turnover → costs → daily PnL. **Write this one twice, independently, by hand — Python-gate rule, no exception for this file.**

**Deliverable:** `engine/` module + `tests/test_engine.py`.

**Acceptance test:** reproduce 12-month-minus-1-month time-series momentum on a handful of the equity/bond ETFs and confirm the sign and rough magnitude match the well-established academic stylized fact (positive average return, Sharpe roughly in the literature's ballpark). This is a correctness unit test, not a research finding — if it fails, the engine has a bug, not an interesting result.

**Standalone claim if shipped here:** "a multi-asset backtest engine with a vol-targeting and turnover-aware cost model" — modest, real, honestly labeled with the cost-model caveat.

---

### 2.2 — v2: The Zoo *(~1.5 days)*

**Goal.** Enumerate the strategy space *before looking at a single result.* This is the step that makes v3's statistics meaningful — if the trial count is fudged or configurations get added after peeking at results, the whole project's epistemic claim collapses.

**Signal families** (all computable from adjusted close/volume alone — no carry, see §0):
- Time-series momentum (multiple lookbacks: 1, 3, 6, 12 months)
- Cross-sectional momentum (rank-based, same lookback set)
- Short-term reversal (1-week, 1-month)
- Volatility-scaling / trend-of-trend (momentum of realized vol itself)

**Grid dimensions:** signal family × lookback × holding period × universe subset (all-44 / equity-only / cross-asset-ex-equity) × sizing rule (equal-weight vs. vol-targeted). Target **300–800 configurations** given the narrower (no-carry) family list — write down the exact count before running anything.

**Builds:**
- `zoo/grid.py` — the enumeration, as literal, inspectable config objects (not generated on the fly at run time).
- `zoo/run_grid.py` — runs every configuration through the v1 engine, collects in-sample Sharpe (and other stats) per configuration.

**Deliverable:**
- **Git commit of `zoo/grid.py` BEFORE `zoo/run_grid.py` is executed even once** — this commit hash is the proof-of-pre-registration you cite in the v3 report. This is the single most important procedural artifact in the whole project.
- `results/zoo_raw_stats.parquet` — one row per configuration, in-sample Sharpe + return stats.
- A histogram figure of the in-sample Sharpe distribution across all trials.

**Standalone claim if shipped here:** none on its own — it's an intermediate artifact. Its value only exists in combination with v3.

---

### 2.3 — v3: False-discovery control *(~2.5 days, THE SHIPPABLE PAPER)*

**Goal.** Answer the question the whole project exists to ask: of everything tried, how much survives once you account for the number of trials?

**Builds:**
- `stats/dsr.py` — Deflated Sharpe Ratio (Bailey & López de Prado, 2014). The core idea: the expected maximum Sharpe under a null of *no* real skill grows with the number of trials $N$, so the observed best Sharpe must be judged against that inflated benchmark, not against zero:
  $$ E[\max SR] \approx \widehat{SR}_0\left[(1-\gamma)\,\Phi^{-1}\!\left(1-\tfrac{1}{N}\right) + \gamma\,\Phi^{-1}\!\left(1-\tfrac{1}{Ne}\right)\right] $$
  ($\gamma$ = Euler–Mascheroni constant, $\widehat{SR}_0$ = cross-sectional std. dev. of trial Sharpes). The Probabilistic Sharpe Ratio is then tested against this adjusted benchmark instead of zero, also correcting for skewness/kurtosis of the strategy's return distribution — implement this correction, don't skip it, since ETF/momentum strategies are reliably non-normal.
- `stats/hlz_haircut.py` — Harvey–Liu–Zhu (2016) multiple-testing haircut: Bonferroni, Holm, and Benjamini-Hochberg-Yekutieli adjusted significance thresholds applied to the full trial set.
- `stats/reality_check.py` — White's Reality Check / Hansen's SPA via **stationary bootstrap** (block bootstrap respecting the time-series autocorrelation in returns — a plain iid bootstrap here would be a quiet correctness bug) on the full strategy-return matrix from v2.
- **Write the DSR and HLZ implementations twice, independently, by hand** — if you can't derive the DSR adjustment at a whiteboard, this version is a liability in an interview, not an asset.

**Deliverable:**
- `report/v3_false_discovery.md` (or compiled PDF) — the actual paper. Structure: trial count (cite the v2 commit hash), raw vs. deflated Sharpe distribution plot, the HLZ-adjusted significance table, the headline finding stated as: **"Of $N$ configurations tried, $k$ survive multiple-testing correction at the 5% level; the best-observed Sharpe of $X$ deflates to $Y$ once trial count and non-normality are accounted for."**
- List of the $k$ surviving configurations — this becomes v4's input.

**Standalone claim if shipped here:** complete and strong on its own. If the sprint has to stop anywhere, stop after v3, not before.

---

### 2.4 — v4: Does the selection generalize? *(~2 days)*

**Goal.** DSR/HLZ tell you the *in-sample* survivors are statistically unusual. They don't tell you whether picking the best one would have actually worked walking forward. This version checks that.

**Builds:**
- `stats/cpcv.py` — Combinatorially Purged Cross-Validation with embargo (López de Prado): split the full sample into $N$ groups, form all valid train/test combinations respecting purging (removing training observations that overlap the test window due to overlapping lookback periods) and an embargo buffer after each test block.
- `stats/pbo.py` — Probability of Backtest Overfitting via CSCV: for each train/test split, check whether the in-sample-best configuration ranks below the out-of-sample median. PBO = the fraction of splits where this happens.
- `stats/walk_forward.py` — honest walk-forward on the v3 survivor list only (not the full 300–800 grid — that would just be v2 again).

**Deliverable:**
- `report/v4_generalization.md` — **a single PBO estimate with its distribution across CSCV splits**, plus a walk-forward equity curve for the top-K v3 survivors overlaid against their in-sample equity curves (the gap between the two lines *is* the finding).
- Explicit statement: "the v3 survivors have a PBO of $p$" — if $p$ is uncomfortably high (e.g., >30–50%), say so plainly rather than cherry-picking a favorable framing. That's the whole point of doing this at all.

**Standalone claim if shipped here:** a complete methodological paper — "which strategies survive false-discovery correction, and do they generalize out-of-sample." Strong, complete, no portfolio required.

---

### 2.5 — v5: The constructive half *(~2 days)* — direct answer to your question

**Goal.** Stop being purely meta. Take whatever survived v3 *and* v4, and build something investable out of it — then report its properties with the same honesty as everything above.

**Builds:**
- `portfolio/covariance.py` — Ledoit–Wolf shrinkage covariance estimator on the surviving strategies' return series (shrinkage matters here specifically because the survivor count is small relative to the estimation window — exactly where sample covariance is worst).
- `portfolio/weights.py` — risk-parity or minimum-variance weighting across survivors, with a vol-target overlay and a drawdown-control rule (e.g., de-risk after a trailing drawdown threshold).
- `portfolio/capacity.py` — using the v1 literature-parameterized cost model, sweep an assumed AUM/turnover relationship and plot Sharpe as a function of size. **Report this as a directional shape, explicitly caveated** (see §0.3) — it shows *where* costs start to bite, not a precise dollar figure, because there's no real calibration behind it without tick data.
- `portfolio/benchmark.py` — comparison against a simple 60/40 (SPY/AGG or similar, trivially constructible from the same panel). SG Trend Index as a secondary trend-following benchmark **only if a free public series can actually be found** — don't force it; the 60/40 comparison alone is sufficient and doesn't depend on finding one.

**Deliverable — this is the direct answer to your question:**

`report/final_portfolio.md` (or PDF) containing:

1. **The survivor ensemble's out-of-sample equity curve** — built only from strategies that passed both v3 (false-discovery) and v4 (generalization) gates.
2. **A bootstrapped confidence interval on the OOS Sharpe ratio** — not a point estimate. This is the single most important number in the whole project: it's the difference between "Sharpe = 1.4" (what every other applicant shows up with) and "Sharpe = 1.4, 90% CI [0.6, 2.1]" (what almost nobody shows up with, and what a real researcher actually wants to see).
3. **A capacity curve** (Sharpe vs. assumed AUM), explicitly labeled as directional/uncalibrated.
4. **Cost drag** — the gap between gross and net-of-cost OOS performance, from the same literature-parameterized model, same caveat.
5. **A benchmark table** — the ensemble vs. 60/40 (and SG Trend if obtainable), across OOS Sharpe, max drawdown, annualized return, turnover.
6. **One paragraph answering the question the entire project was built to ask:** *after enumerating hundreds of strategies, correcting for how many were tried, and checking that the survivors generalize out-of-sample — what, if anything, is actually left?* The honest answer might be "a modest but real risk-parity-flavored momentum sleeve with Sharpe ~0.X and wide uncertainty bounds" — that is a *good* answer, not a disappointing one, because almost nobody else can produce the audit trail proving it wasn't luck.

**Standalone claim if shipped here:** the complete project — "I found something, and I can prove I didn't find it by accident." Best-case outcome of the whole 20-day sprint.

---

## 3. Reading, mapped to the version that needs it

Same list as the sprint plan, repeated here so this doc is self-contained:

| Reading | Needed for | Read by |
|---|---|---|
| Bailey & López de Prado, *The Deflated Sharpe Ratio* (2014) | v3 | before starting v3 |
| Harvey, Liu & Zhu, *…and the Cross-Section of Expected Returns* (2016) | v3 | before starting v3 |
| Corwin & Schultz, *A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices* (2012) | v1 cost model | before starting v1 |
| López de Prado, *Advances in Financial Machine Learning*, ch. 7 (purged CV) and 11–12 | v4 | before starting v4 |
| Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting* | v4 | before starting v4 |
| Ledoit & Wolf, *Honey, I Shrunk the Sample Covariance Matrix* (2004) | v5 | before starting v5 |

---

## 4. Repo structure (target, by v5)

```
z1/
├── data/
│   ├── pull_yfinance.py
│   ├── pull_stooq.py
│   ├── clean.py
│   ├── MANIFEST.md
│   └── processed/panel.parquet
├── engine/
│   ├── signals.py
│   ├── sizing.py
│   ├── costs.py
│   └── backtest.py
├── zoo/
│   ├── grid.py              # committed BEFORE run_grid.py is ever executed
│   └── run_grid.py
├── stats/
│   ├── dsr.py
│   ├── hlz_haircut.py
│   ├── reality_check.py
│   ├── cpcv.py
│   ├── pbo.py
│   └── walk_forward.py
├── portfolio/
│   ├── covariance.py
│   ├── weights.py
│   ├── capacity.py
│   └── benchmark.py
├── tests/
│   └── test_engine.py       # the 12-1 momentum correctness check
├── report/
│   ├── v3_false_discovery.md
│   ├── v4_generalization.md
│   └── final_portfolio.md
└── README.md
```

## 5. Non-negotiables carried from the sprint plan

- Enumerate the grid before looking at a single result (§2.2) — the entire epistemic claim of the project depends on this.
- `engine/backtest.py`, `stats/dsr.py`, `stats/hlz_haircut.py` written twice, independently, by hand.
- Every artifact touching the cost model carries the "literature-parameterized, not calibrated" footnote — no exceptions, no forgetting it in a later version.
- Ship at whichever version is complete when time runs out. v3 is a complete paper on its own; v4 and v5 are upside, not requirements.
