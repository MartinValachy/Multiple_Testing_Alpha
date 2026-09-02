# v3 figure: the whole point of the project on a graph
#
# histogram of all 780 in-sample sharpes, with 2 vertical lines on it:
#   1) what the BEST of 780 tries is expected to be if NO strategy has any skill (the DSR null benchmark)
#   2) the best I actually observed
# if those two lines sit almost on top of each other, the best config isnt special, its just the top of 780 coinflips.
#
# no need to re run the grid for this, run_grid.py saves the annualized sharpe per config and dsr.py works in daily units, and daily = annualized / sqrt(252), so the parquet already has everything

import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed, just save the figure
import matplotlib.pyplot as plt

from dsr import expected_max_sharpe_null

STATS_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "zoo_raw_stats.parquet")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "v3_sharpe_vs_null.png")

TRADING_DAYS_PER_YEAR = 252


def main():
    #load the v2 grid results
    results = pd.read_parquet(STATS_PATH)
    annualized = results["gross_sharpe"].dropna()

    # dsr.py works in daily units so convert, run the null benchmark, then convert back for the plot
    daily = annualized / np.sqrt(TRADING_DAYS_PER_YEAR)
    sr_0 = daily.std()
    sr_star_daily = expected_max_sharpe_null(sr_0, len(daily))
    sr_star = sr_star_daily * np.sqrt(TRADING_DAYS_PER_YEAR)

    observed_max = annualized.max()

    #now the actual figure
    plt.figure(figsize=(10, 6))
    plt.hist(annualized, bins=50, color="#9ecae1", edgecolor="white", label="780 configs")
    #format the axis
    plt.axvline(sr_star, color="#d62728", linestyle="--", linewidth=2, label="expected best if nothing has skill (%.2f)" % sr_star)
    plt.axvline(observed_max, color="#2b2b2b", linestyle="-", linewidth=2, label="best actually observed (%.2f)" % observed_max)
    #axis label
    plt.xlabel("in-sample annualized gross Sharpe")
    plt.ylabel("number of configs")
    #title
    plt.title("Z1 v3: the best of 780 tries against what luck alone gives you")
    #legend
    plt.legend()
    plt.tight_layout()
    #save it
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    plt.savefig(OUT_PATH, dpi=150)
    print("saved to: " + OUT_PATH)


if __name__ == "__main__":
    main()
