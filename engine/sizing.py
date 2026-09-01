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


def equal_weight(signal: pd.Series, target_vol: float) -> pd.Series:
    # v2.3, the grid's other sizing rule: same bet size regardless of how volatile the asset is (unlike vol_target_weight, no division by realized vol). 
    # direction/strength still comes from the signal's sign and magnitude, just not risk normalized against the asset's vol. 
    # target_vol reused here as the flat size, jsut so that equal_weight and vol_targeted configs are in similar magnitude range for given target vol
    return signal * target_vol



def turnover(weights: pd.Series):
    #returns the absolute difference in weights
    return weights.diff().abs()


def apply_holding_period(weights: pd.Series, holding_period_days: int) -> pd.Series:
    #make an all false mask
    mask = pd.Series(False, index=weights.index)
    #flip every n'th position to true, depending on holdin_period_days
    mask.iloc[::holding_period_days] = True
    # keep weights' values only where mask == true, and fill the others with NaN
    weights = weights.where(mask)
    weights = weights.ffill()
    return weights
