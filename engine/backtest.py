# v1.3 — the backtest loop
# Spec: Z1_Version_Spec.md §2.1, §5 non-negotiable
#
# THIS FILE MUST BE HAND-WRITTEN TWICE, INDEPENDENTLY. Write it once, get
# it working, then set it aside and write it again from scratch (not
# copy-paste, not "look at v1 while typing v2") — the second pass is what
# proves you actually understand the logic, not just that it ran once.
#
# What it does: takes a signal + prices, turns it into a daily PnL series.
#   signal -> target weight (sizing.py) -> turnover (sizing.py)
#   -> cost drag (costs.py) -> daily PnL = weight * asset_return - cost_drag
#
# This ties together everything in signals.py, sizing.py, costs.py — a
# bug here is a bug in every backtest that ever runs through this engine,
# which is why "correctness matters more than sophistication" (spec's
# own words for this file).

import pandas as pd

from signals import return_over_lookback
from sizing import vol_target_weight, turnover
from costs import corwin_schultz_spread


def run_backtest(prices: pd.Series, high: pd.Series, low: pd.Series,
                  lookback_days: int, vol_window: int, target_vol: float) -> pd.DataFrame:
   #what do you feed into return_over_lookback? What price series, what lookback?
   signal = return_over_lookback(prices, lookback_days)
   #shifted to avoid look ahead bias
   weights = vol_target_weight(prices.shift(1), signal.shift(1), vol_window, target_vol)
   turn_over = turnover(weights)
   costs = turn_over*corwin_schultz_spread(high, low)
   returns_gross = weights * prices.pct_change()
   returns_net = returns_gross - costs
   return returns_net
