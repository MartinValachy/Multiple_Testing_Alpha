# v1.1: sizing, volatility targeting + turnover



# signals.py gives "which direction, how strong" 
# Now the question: how big of a position


import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def annualized_vol(prices: pd.Series, vol_window: int):
    #make again a pd of daily returns
    daily_returns = prices.pct_change()
    # rolling daily vol of last (vol_window) days
    rolling_daily_vol = daily_returns.rolling(vol_window).std()
    #now we must annualize it by * sqrt(days per year)
    rolling_annualized_vol = rolling_daily_vol*np.sqrt(TRADING_DAYS_PER_YEAR)
    return rolling_annualized_vol


def vol_target_weight(prices: pd.Series, signal: pd.Series, vol_window: int, target_vol: float):
    #load annualized vol rolling daily
    vol = annualized_vol(prices, vol_window)
    #scale the position based on vol
    scalar = target_vol / vol
    weight = signal * scalar
    return weight



def turnover(weights: pd.Series):
    #returns the absolute difference in weights
    return weights.diff().abs()
