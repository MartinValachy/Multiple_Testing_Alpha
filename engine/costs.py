# v1.2 literature-parameterized cost model
#
# IMPORTANT cost estimate is from literatur, not empirical, treat the magnitued as more like directions
#
# Corwin & Schultz (2012) gives an estimation of a bid-ask spread from just daily high/low prices
# Done by 3 numbers per pair of days: beta, gamma, alpha 

import numpy as np
import pandas as pd

# constant from the Corwin-Schultz paper, 3 - 2*sqrt(2)
CS_CONSTANT = 3 - 2 * np.sqrt(2)


def compute_beta(high: pd.Series, low: pd.Series) -> pd.Series:
    #beta = expected (sum over today and yesterday of [ln(high/low)]^2)
    day_t = (np.log(high/low))**2
    return day_t + day_t.shift(1) # type: ignore
    

def compute_gamma(high: pd.Series, low: pd.Series):
    # gamma = ln(2 day high / 2 day low) ^2
    two_day_high = high.rolling(2).max()
    two_day_low = low.rolling(2).min()
    gamma = (np.log(two_day_high / two_day_low)) ** 2
    return gamma

def compute_alpha(beta: pd.Series, gamma: pd.Series) -> pd.Series:
    # alpha = (sqrt(2*beta) - sqrt(beta)) / CS_CONSTANT - sqrt(gamma / CS_CONSTANT)
    return (np.sqrt(2 * beta) - np.sqrt(beta)) / CS_CONSTANT - np.sqrt(gamma / CS_CONSTANT)


def alpha_to_spread(alpha: pd.Series) -> pd.Series:
    #S = 2*(e^alpha - 1) / (1 + e^alpha)
    S = 2*(np.exp(alpha)-1)/(1+np.exp(alpha))
    return S.clip(lower=0)

def corwin_schultz_spread(high: pd.Series, low: pd.Series) -> pd.Series:
    beta = compute_beta(high, low)
    gamma = compute_gamma(high, low)
    alpha = compute_alpha(beta, gamma)
    Spread = alpha_to_spread(alpha)
    return Spread

#how much does the price move, per dollar of trading volume??
def amihud_illiquidity(prices: pd.Series, dollar_volume: pd.Series, window: int) -> pd.Series:
    #ILLIQ = mean( |daily return| / dollar volume )
    daily_returns = prices.pct_change()
    #now calc the ratio of abs(returns) to dollar vol
    ratio = daily_returns.abs() / dollar_volume
    #return the mean in the window given
    return ratio.rolling(window).mean()