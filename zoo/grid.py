# v2 strategy grid enumeration

# The commit of this file is the proof of pre registration, evidence the grid wasn't falsfied 
# This file only defines WHAT will be tried, simply a list of config dictionarie
#
# 780 configs. More trials would raise the bar in v3 DSR correction, not giving "more chances to find something" 

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from pull_yfinance import TICKERS as TICKERS_BY_BUCKET


# dimension 1: signal family + lookback (in trading days)

MONTHLY_LOOKBACKS_DAYS = [21, 63, 126, 252]   # 1, 3, 6, 12 months

SIGNAL_FAMILIES = {
    "tsmom": MONTHLY_LOOKBACKS_DAYS,
    "cross_sectional_momentum": MONTHLY_LOOKBACKS_DAYS,
    "short_term_reversal": [5, 21],            # 1 week, 1 month
    "vol_of_vol": MONTHLY_LOOKBACKS_DAYS,
}

# dimension 1b: skip-most-recent-month variant 
# the 12-1 from v1's acceptance test, skip the most recent month so short-term reversal doesn't contaminate a momentum signal
# only makes sense for the momentum style families;

SKIP_MONTH_ELIGIBLE_FAMILIES = ["tsmom", "cross_sectional_momentum", "vol_of_vol"]
SKIP_MONTH_LAG_DAYS = 21   # ca 1 month, matches v1's signal_lag_days=21

# dimension 2: holding(rebalancing) period 
# not spec-mandated with specific values, this is an open design choice, spaced out so each option isnt simply a filler.
# "daily" means re-signal every day 
# the others need a rebalance-frequency control that doesn't exist in engine/backtest.py yet
HOLDING_PERIODS = ["daily", "weekly", "monthly", "quarterly", "semiannual"]

# dimension 3: universe subsets

EQUITY_TICKERS = TICKERS_BY_BUCKET["Equity"]
NON_EQUITY_TICKERS = [t for bucket, tickers in TICKERS_BY_BUCKET.items() if bucket != "Equity"for t in tickers]
ALL_TICKERS = EQUITY_TICKERS + NON_EQUITY_TICKERS

UNIVERSE_SUBSETS = {
    "all_44": ALL_TICKERS,
    "equity_only": EQUITY_TICKERS,
    "cross_asset_ex_equity": NON_EQUITY_TICKERS,
}

# dimension 4: sizing rule 
SIZING_RULES = ["equal_weight", "vol_targeted"]

# now building the trading strat grid
def build_grid() -> list[dict]:
    configs = []
    config_id = 0

    for signal_family, lookbacks in SIGNAL_FAMILIES.items():
        if signal_family in SKIP_MONTH_ELIGIBLE_FAMILIES:
            skip_month_options = [False, True]
        else:
            skip_month_options = [False]
        #nested categories
        for lookback_days in lookbacks:
            for skip_month in skip_month_options:
                for holding_period in HOLDING_PERIODS:
                    for universe_name in UNIVERSE_SUBSETS:
                        for sizing_rule in SIZING_RULES:
                            configs.append({
                                "config_id": config_id,
                                "signal_family": signal_family,
                                "lookback_days": lookback_days,
                                "skip_month": skip_month,
                                "signal_lag_days": SKIP_MONTH_LAG_DAYS if skip_month else 0,
                                "holding_period": holding_period,
                                "universe_subset": universe_name,
                                "sizing_rule": sizing_rule,
                            })
                            config_id += 1
    return configs


def main():
    configs = build_grid()
    print("total configs: ",  str(len(configs)))
    print()
    print("breakdown by signal_family:")
    print()
    # count strategies in each signal family
    for family in SIGNAL_FAMILIES:
        count = sum(1 for c in configs if c["signal_family"] == family)
        print(str(family)+ ": "+str(count))



if __name__ == "__main__":
    main()
