# v1.3 backtest for a strategy
# Takes a signal + prices, turns it into a daily pnl series
# signal to target weight to turnover to costs to daily pnl

import pandas as pd

from signals import return_over_lookback, cross_sectional_signal
from sizing import vol_target_weight, equal_weight, turnover, apply_holding_period
from costs import corwin_schultz_spread, average_dollar_volume, apply_liquidity_ceiling

# v2.0 split: apply_backtest is the family adjusted function (weight -> turnover -> cost -> pnl).
# It takes a signal already built by whichever family constructed it

# volume is needed to see how liquid the ticker is, the liquidity is used to bound the corwin-schultz cost estimate
# holding_period_days=1 (daily) and sizing_rule="vol_targeted" are the defaults —
# matches everything already tested, no behavior change unless a caller asks for something else
def apply_backtest(signal: pd.Series, prices: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series, vol_window: int, target_vol: float, holding_period_days: int = 1, sizing_rule: str = "vol_targeted") -> pd.DataFrame:
   #shifted to avoid look ahead bias
   # split based on sizing rule: either vol targeted or equal weight.
   if sizing_rule == "vol_targeted":
      weights = vol_target_weight(prices.shift(1), signal.shift(1), vol_window, target_vol)
   elif sizing_rule == "equal_weight":
      weights = equal_weight(signal.shift(1), target_vol)
   else:
      raise ValueError(f"unknown sizing_rule: {sizing_rule}")
   # v2.2: freeze the weight between rebalance dates instead of letting it drift daily
   weights = apply_holding_period(weights, holding_period_days)
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


#signal_lag_days allows for ignoring N days when looking at returns, volatility ... Default is 0 so nothing basically changes
# this is the tsmom specific signal construction, kept as its own function (same name as before the split, so nothing else breaks) —
# it just delegates the weight/turnover/cost/pnl part to apply_backtest now
def run_backtest(prices: pd.Series, high: pd.Series, low: pd.Series, volume: pd.Series, lookback_days: int, vol_window: int, target_vol: float, signal_lag_days: int = 0, holding_period_days: int = 1, sizing_rule: str = "vol_targeted") -> pd.DataFrame:
   #load signal
   signal = return_over_lookback(prices.shift(signal_lag_days), lookback_days)
   return apply_backtest(signal, prices, high, low, volume, vol_window, target_vol, holding_period_days, sizing_rule)


# v2.1: cross-sectional momentum across a whole universe at once, not one ticker at a time. 
# prices_by_ticker/highs_by_ticker/etc are dicts keyed by ticker (same key in each dict)
# Returns a dict of apply_backtest-style DFs, one per ticker
# basically same output shape as run_backtest's output, just built from a cross-sectional signal

def run_cross_sectional_backtest(prices_by_ticker: dict, highs_by_ticker: dict, lows_by_ticker: dict, volumes_by_ticker: dict, lookback_days: int, vol_window: int, target_vol: float, signal_lag_days: int = 0, holding_period_days: int = 1, sizing_rule: str = "vol_targeted") -> dict:
   # build the wide raw momentum panel, one column per ticker
   raw_signals = {}
   for ticker, prices in prices_by_ticker.items():
      raw_signals[ticker] = return_over_lookback(prices.shift(signal_lag_days), lookback_days)
   raw_signal_df = pd.DataFrame(raw_signals)

   # rank tickers against each other each day, centered to cca [-1, 1]
   cs_signal_df = cross_sectional_signal(raw_signal_df)

   # each ticker's cross sectional signal goes through the exact same weight/turnover/cost/pnl engine as tsmom/reversal/vol-of-vol
   results = {}
   for ticker in prices_by_ticker:
      signal = cs_signal_df[ticker]
      results[ticker] = apply_backtest(
          signal,
          prices_by_ticker[ticker],
          highs_by_ticker[ticker],
          lows_by_ticker[ticker],
          volumes_by_ticker[ticker],
          vol_window,
          target_vol,
          holding_period_days,
          sizing_rule,
      )
   return results
