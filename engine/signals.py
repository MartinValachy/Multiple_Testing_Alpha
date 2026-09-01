# v1.0 signal primitives
# 

# Every fct takes a price series (Close or Adj Close, by date ascend.)
# returns a signal series of the same length


import pandas as pd


def return_over_lookback(prices: pd.Series, lookback_days: int):
    # put for each day, the returns made over the last (lookback_days) trading days
    returns = prices.pct_change(periods=lookback_days)
    return returns


def vol_scaled_return(prices: pd.Series, lookback_days: int, vol_window: int):
    # for each day, put return per unit of vol of return of (lookback_days) and of volatility of (vol_window)
    returns = return_over_lookback(prices, lookback_days)
    daily_returns = prices.pct_change()
    vol_in_vol_window = daily_returns.rolling(vol_window).std()
    return returns/vol_in_vol_window


def cross_sectional_rank(signal_by_ticker: pd.DataFrame):
    #rank all the tickers against each other, ascending
    df_ranked = signal_by_ticker.rank(axis=1, pct=True)
    return df_ranked


def cross_sectional_signal(signal_by_ticker: pd.DataFrame) -> pd.DataFrame:
    rank = cross_sectional_rank(signal_by_ticker)
    rank_adj = (rank- 0.5)*2
    return rank_adj
