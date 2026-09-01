# v1.3 backtest for a strategy
# Takes a signal + prices, turns it into a daily pnl series
# signal to target weight to turnover to costs to daily pnl

import pandas as pd

from signals import return_over_lookback
from sizing import vol_target_weight, turnover
from costs import corwin_schultz_spread, average_dollar_volume, apply_liquidity_ceiling

#signal_lag_days allows for ignoring N days when looking at returns, volatility ... Default is 0 so nothing basically changes
# volume is needed now too, to work out how liquid this ticker actually is 
# the liquidity is used to bound corwin shultz cost estimate, it overestimates costs for high-liquidity tickers
def run_backtest(prices: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series, lookback_days: int, vol_window: int, target_vol: float, signal_lag_days: int = 0) -> pd.DataFrame:
   #load signal
   signal = return_over_lookback(prices.shift(signal_lag_days), lookback_days)
   #shifted to avoid look ahead bias
   weights = vol_target_weight(prices.shift(1), signal.shift(1), vol_window, target_vol)
   # calc turnover for cost estimates
   turn_over = turnover(weights)

   #corwin schultz gives the day to day shape, cap it at whats realistic for this ticker(by liquidity tiers)

   raw_spread = corwin_schultz_spread(high, low)
   avg_dollar_vol = average_dollar_volume(prices, volume)
   capped_spread = apply_liquidity_ceiling(raw_spread, avg_dollar_vol)

   #costs for transactions from turnover
   costs = turn_over*capped_spread
   
   gross_return = weights * prices.pct_change()
   net_return = gross_return - costs

   return pd.DataFrame({
       "weight": weights,
       "turnover": turn_over,
       "cost": costs,
       "gross_return": gross_return,
       "net_return": net_return,
   })
