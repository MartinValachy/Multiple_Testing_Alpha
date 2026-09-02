# v3 White's Reality Check / Hansen's SPA, 
# with a stationary bootstrap (Politis & Romano 1994).
#
# a normal bootstrap would ignore the autocorrelation in daily returns the stationary bootstrap resamples random-length BLOCKS
# instead of single rows, and applies the SAME resampled date sequence across every trial at once, 
# so it preserves both time-series autocorrelation and cross-trial correlation.

import numpy as np
import pandas as pd


def stationary_bootstrap_indices(t_len: int, mean_block_length: float) -> np.ndarray:
    # probability of continuing the current block vs starting a new one
    p_continue = 1 - 1 / mean_block_length
    #prepare the bootstrap and set up the beginning with a random one 
    idx = np.empty(t_len, dtype=int)
    idx[0] = np.random.randint(t_len)
    #then for the remaining blocks:
    for t in range(1, t_len):
        #given the probability, if the random draw succeeds, extend/continue the block, otherwise new one.
        if np.random.rand() < p_continue:
            idx[t] = (idx[t - 1] + 1) % t_len  # continue the block
        else:
            idx[t] = np.random.randint(t_len)  # start a new block, random point
    return idx


def reality_check_p_value(returns_wide: pd.DataFrame, n_bootstrap: int = 500, mean_block_length: float = 20) -> dict:
    # only the fully-overlapping window, every trial needs a value on every resampled date for the joint resample to make sense
    common = returns_wide.dropna()
    values = common.values
    # test the null hypothesis "the best-performing strategy isn't actually good, it just got lucky given how many you tried."
    # by demeaning first, every trial is forced to have zero true average return by construction
    demeaned = values - values.mean(axis=0, keepdims=True)

    observed_max_mean = values.mean(axis=0).max()
    #number of days T in the fully overlapping window
    t_len = len(common)
    # pre allocate an array to hold one number per bootstrap replicate
    null_maxes = np.empty(n_bootstrap)
    # repeat the resampling 500 times
    for b in range(n_bootstrap):
        # generate one sequence of t_len resampled day indices using the stationary bootstrap
        idx = stationary_bootstrap_indices(t_len, mean_block_length)
        #apply the index to all days
        resampled = demeaned[idx, :]
        #For this one bootstrap draw, compute the mean return of each of the 780 trials over the resampled path and take max
        null_maxes[b] = resampled.mean(axis=0).max()
    #boolean array of length n-bootstrap, true when a null-world "best of 780" was at least as big as what you actually observed in the real data
    p_value = float((null_maxes >= observed_max_mean).mean())

    return {
        "t_len": t_len,
        "n_trials": values.shape[1],
        "n_bootstrap": n_bootstrap,
        "mean_block_length": mean_block_length,
        "observed_max_mean": float(observed_max_mean),
        "null_maxes": null_maxes,
        "p_value": p_value,
    }
