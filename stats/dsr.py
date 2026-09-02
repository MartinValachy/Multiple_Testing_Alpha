# v3: Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
#
# idea: 
# the expected MAXIMUM sharpe across N trials grows with N even without skill, 
# so the observed best sharpe has to be judged against that inflated benchmark, not against zero
# then the probabilistic sharpe ratio (PSR) tests the best trial against that benchmark, 
# correcting for its own skew/kurtosis too, since momentum strategies are non-normal.

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

GAMMA_EM = 0.5772156649015328  # euler-mascheroni constant

def expected_max_sharpe_null(sr_0: float, n_trials: int) -> float:
    # E[max SR] = sr_0 * [(1-gamma)*Phi^(-1)(1-1/N) + gamma*Phi^(-1)(1-1/(N*e))]
    # sr_0 = cross-sectional std of trial sharpes 
    z1 = norm.ppf(1 - 1 / n_trials)
    z2 = norm.ppf(1 - 1 / (n_trials * np.e))
    return sr_0*((1 - GAMMA_EM) * z1 + GAMMA_EM * z2)  # type: ignore


def probabilistic_sharpe_ratio(sr_hat: float, sr_star: float, n_obs: int, strategy_skew: float, strategy_kurtosis: float) -> float:
    # PSR(SR*) = normdistr( [(SR_hat - SR*) * sqrt(T-1)] / [sqrt(1 - skew*SR_hat + (kurt-1)/4 * SR_hat^2)] )
    # strategy_kurtosis is non-excess
    numerator = (sr_hat - sr_star) * np.sqrt(n_obs - 1)
    denominator = np.sqrt(1 - strategy_skew * sr_hat + ((strategy_kurtosis - 1) / 4) * sr_hat**2)
    return norm.cdf(numerator / denominator) #type: ignore


def deflated_sharpe_ratio(trial_daily_sharpes: pd.Series, winning_trial_daily_returns: pd.Series) -> dict:
    # every trial's daily sharpe (for sr_0/N) + the above zero trial's own daily return series (for its skew/kurtosis)
    n_trials = len(trial_daily_sharpes)
    # sr_0 = cross-sectional std of trial sharpes 
    sr_0 = trial_daily_sharpes.std()
    # expected max sharpe null = SR*
    sr_star = expected_max_sharpe_null(sr_0, n_trials)
    # max sharpe in trials = sr_hat
    sr_hat = trial_daily_sharpes.max()
    # just drop the NaN days from the winning trial's own return series
    returns = winning_trial_daily_returns.dropna()
    n_obs = len(returns)
    #now calc the skew and kurtosis
    strategy_skew = skew(returns)
    strategy_kurtosis = kurtosis(returns, fisher=False)
    # and finally get the deflated Sharpe ratio
    dsr = probabilistic_sharpe_ratio(sr_hat, sr_star, n_obs, strategy_skew, strategy_kurtosis)

    return {
        "n_trials": n_trials,
        "sr_0_daily": sr_0,
        "expected_max_sharpe_null_daily": sr_star,
        "best_daily_sharpe": sr_hat,
        "best_n_obs": n_obs,
        "best_skew": strategy_skew,
        "best_kurtosis_nonexcess": strategy_kurtosis,
        "dsr": dsr,
    }
