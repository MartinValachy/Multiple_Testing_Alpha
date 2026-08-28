# v1.3 backtest for a strategy
# Takes a signal + prices, turns it into a daily pnl series
# signal to target weight to turnover to costs to daily pnl

import pandas as pd

from signals import return_over_lookback
from sizing import vol_target_weight, turnover
from costs import corwin_schultz_spread


def run_backtest(prices: pd.Series, high: pd.Series, low: pd.Series, lookback_days: int, vol_window: int, target_vol: float) -> pd.DataFrame:
   #what do you feed into return_over_lookback? What price series, what lookback?
   signal = return_over_lookback(prices, lookback_days)
   #shifted to avoid look ahead bias
   weights = vol_target_weight(prices.shift(1), signal.shift(1), vol_window, target_vol)
   # how much does the portfolio change per day, meaning costs per transaction
   turn_over = turnover(weights)
   #costs for transactions from turnover
   costs = turn_over*corwin_schultz_spread(high, low)
   pnl = weights * prices.pct_change() - costs
   return pnl
