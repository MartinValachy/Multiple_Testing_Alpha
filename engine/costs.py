# v1.2 literature parameterized Corwin Shutz cost model and hihg-liquidity ticker bip spread ceiling
#
# IMPORTANT cost estimate is from literatur, not empirical, treat the magnitued as more like directions
#
# Corwin & Schultz (2012) gives an estimation of a bid-ask spread from just daily high/low prices
# Done by 3 numbers per pair of days: beta, gamma, alpha 

import numpy as np
import pandas as pd

# constant from the Corwin-Schultz paper: 3 - 2*sqrt(2)
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
    return S.clip(lower=0)# type: ignore

def corwin_schultz_spread(high: pd.Series, low: pd.Series) -> pd.Series:
    beta = compute_beta(high, low)
    gamma = compute_gamma(high, low)
    alpha = compute_alpha(beta, gamma)# type: ignore
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

#But almost all high liquidity tickers have really tight spreads, therefore we need to categorize these and put a ceiling on the spreads

#Corwin Schutz  just reads high-low ranges and it overestimates spreads badly for high liquidity tickers
# These "settings" are not calibrated to reach certain results, its known and  published typical spread levels for ETFs this big 


# bps ceiling per tier, general typical spread levels for big ETFs
SPREAD_CEILING_BPS = {
    "ultra_liquid": 1.5,   # SPY/QQQ/GLD types, trades always
    "liquid": 4,           # big bond ETFs,... still trade a lot
    "less_liquid": 12,     # smaller intl/commodity/FX/real estate, trades less
}

# I will assign the tier automatically based on liquidity tresholds. (Close * volume)
# 
#   > 1B/day    -> ultra_liquid  
#   > 100M/day  -> liquid        
#   below that  -> less_liquid   

ULTRA_LIQUID_MIN_DOLLAR_VOLUME = 1_000_000_000
LIQUID_MIN_DOLLAR_VOLUME = 100_000_000


RECENT_LIQUIDITY_WINDOW_DAYS = 200  # ~1 trading year


def average_dollar_volume(prices: pd.Series, volume: pd.Series) -> float:
    # dollar volume per day = price * volume
    dollar_volume = prices * volume
    # only the last ca. 200 trading days
    recent = dollar_volume.iloc[-RECENT_LIQUIDITY_WINDOW_DAYS:]
    return recent.mean()

#assign liquidity tiers

def liquidity_tier(avg_dollar_volume: float) -> str:
    if avg_dollar_volume >= ULTRA_LIQUID_MIN_DOLLAR_VOLUME:
        return "ultra_liquid"
    elif avg_dollar_volume >= LIQUID_MIN_DOLLAR_VOLUME:
        return "liquid"
    else:
        return "less_liquid"

#assing bps and give cost % estimate
def spread_ceiling(avg_dollar_volume: float) -> float:
    tier = liquidity_tier(avg_dollar_volume)
    bps = SPREAD_CEILING_BPS[tier]
    # bps to decimal,for example 2 bps -> 0.0002
    return bps / 10000


def apply_liquidity_ceiling(spread: pd.Series, avg_dollar_volume: float) -> pd.Series:
    # caps the spread at the ceiling, but keeps the corwin shutz for classic day-to-day trading
    ceiling = spread_ceiling(avg_dollar_volume)
    return spread.clip(upper=ceiling)