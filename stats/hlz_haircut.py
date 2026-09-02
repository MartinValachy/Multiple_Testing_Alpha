# v3 multiple-testing haircut, Harvey, Liu & Zhu (2016).
#
# 3 corrections, loosest to strictest-under-dependence:
# Bonferroni (controls family error, assumes nothing about dependence, most conservative)
# Holm (step-down version of Bonferroni, slightly less harsh)
# Benjamini-Hochberg-Yekutieli (controls false discovery rate, valid under ARBITRARY dependence, 
# the correct one for my situation, since a lot of these trials are correlated with each 

import numpy as np
import pandas as pd
from scipy.stats import norm


def trial_p_values(daily_sharpe: pd.Series, n_obs: pd.Series) -> pd.Series:
    # one sided p-value per trial, H0: true mean return = 0, t-stat approx: daily sharpe * sqrt(n observations)
    t_stat = daily_sharpe * np.sqrt(n_obs)
    p = 1 - norm.cdf(t_stat)
    return pd.Series(p, index=daily_sharpe.index)


def bonferroni_survivors(p_values: pd.Series, alpha: float = 0.05) -> int:
    #simply make the requirement harsher based on the number of trials
    n = len(p_values)
    threshold = alpha / n
    return int((p_values <= threshold).sum())


def holm_survivors(p_values: pd.Series, alpha: float = 0.05) -> int:
    #sort the pvalues values
    n = len(p_values)
    sorted_p = np.sort(p_values.values)     # type: ignore
    # threshold gets looser as you go down the sorted list
    thresholds = alpha / (n - np.arange(n))
    passed = sorted_p <= thresholds
    if passed.all():
        return n
    # first one that fails, then everything before it survives, everything after doesn't
    return int(np.argmax(~passed))


def bhy_survivors(p_values: pd.Series, alpha: float = 0.05) -> int:
    #first step for any step-up FDR procedure is sort all n pvalues ascending
    n = len(p_values)
    sorted_p = np.sort(p_values.values)     # type: ignore
    #c(n) = 1 + 1/2 + 1/3 + ... + 1/n, the n-th harmonic number
    c_n = np.sum(1.0 / np.arange(1, n + 1))
    #build the BH(Y) critical value at each rank i: (i/n) * alpha / c(n).
    thresholds = (np.arange(1, n + 1) / n) * (alpha / c_n)
    #at each rank, is the sorted p-value below its critical line?
    passed = sorted_p <= thresholds
    #find the largest k such that sorted_p[k] <= threshold[k],
    # then declare the first k sorted p-values (1 through k) as discoveries
    if not passed.any():
        return 0
    return int(np.max(np.where(passed)[0]) + 1)


def hlz_haircut(daily_sharpe: pd.Series, n_obs: pd.Series, alpha: float = 0.05) -> dict:
    #load all pvalues
    p_values = trial_p_values(daily_sharpe, n_obs)
    #call all 3 tests
    return {
        "n_trials": len(p_values),
        "alpha": alpha,
        "raw_survivors": int((p_values < alpha).sum()),
        "bonferroni_survivors": bonferroni_survivors(p_values, alpha),
        "holm_survivors": holm_survivors(p_values, alpha),
        "bhy_survivors": bhy_survivors(p_values, alpha),
    }
