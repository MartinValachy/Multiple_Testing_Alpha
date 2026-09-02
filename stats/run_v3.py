# v3 runs the full program: re-runs the 780-config grid for full daily series
# then DSR + HLZ + Reality Check on top of it.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "zoo"))

import numpy as np
import pandas as pd

from grid import build_grid, UNIVERSE_SUBSETS, ALL_TICKERS
from backtest import run_backtest, run_cross_sectional_backtest, apply_backtest
from signals import return_over_lookback
from sizing import annualized_vol
from dsr import deflated_sharpe_ratio
from hlz_haircut import hlz_haircut, trial_p_values
from reality_check import reality_check_p_value

PANEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "panel.parquet")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "report", "v3_false_discovery.md")
# setup the variables
VOL_WINDOW = 20
TARGET_VOL = 0.10
TRADING_DAYS_PER_YEAR = 252
HOLDING_PERIOD_DAYS = {"daily": 1, "weekly": 5, "monthly": 21, "quarterly": 63, "semiannual": 126}
PRE_REGISTRATION_COMMIT = "01e84db"

#load the database of tickers
def get_series(panel, ticker, field):
    sub = panel[(panel["ticker"] == ticker) & (panel["field"] == field)]
    return sub.set_index("date")["value"].sort_index()

#load the ticker data
def load_all_ticker_data(panel):
    data = {}
    for ticker in ALL_TICKERS:
        data[ticker] = {
            "close": get_series(panel, ticker, "Close"),
            "high": get_series(panel, ticker, "High"),
            "low": get_series(panel, ticker, "Low"),
            "volume": get_series(panel, ticker, "Volume"),
        }
    return data

# basically same as in run_grid.py, but now i want it in this one python file
def run_one_config_series(config, ticker_data):
    universe = UNIVERSE_SUBSETS[config["universe_subset"]]
    holding_days = HOLDING_PERIOD_DAYS[config["holding_period"]]
    signal_lag = config["signal_lag_days"]
    family = config["signal_family"]

    if family == "cross_sectional_momentum":
        prices = {t: ticker_data[t]["close"] for t in universe}
        highs = {t: ticker_data[t]["high"] for t in universe}
        lows = {t: ticker_data[t]["low"] for t in universe}
        volumes = {t: ticker_data[t]["volume"] for t in universe}
        per_ticker_results = run_cross_sectional_backtest(
            prices, highs, lows, volumes,
            lookback_days=config["lookback_days"], vol_window=VOL_WINDOW,
            target_vol=TARGET_VOL, signal_lag_days=signal_lag,
            holding_period_days=holding_days, sizing_rule=config["sizing_rule"],
        )
    else:
        per_ticker_results = {}
        for ticker in universe:
            close = ticker_data[ticker]["close"]
            high = ticker_data[ticker]["high"]
            low = ticker_data[ticker]["low"]
            volume = ticker_data[ticker]["volume"]

            if family == "tsmom":
                per_ticker_results[ticker] = run_backtest(
                    close, high, low, volume,
                    lookback_days=config["lookback_days"], vol_window=VOL_WINDOW,
                    target_vol=TARGET_VOL, signal_lag_days=signal_lag,
                    holding_period_days=holding_days, sizing_rule=config["sizing_rule"],
                )
            elif family == "short_term_reversal":
                raw_signal = -return_over_lookback(close, config["lookback_days"])
                per_ticker_results[ticker] = apply_backtest(
                    raw_signal, close, high, low, volume,
                    vol_window=VOL_WINDOW, target_vol=TARGET_VOL,
                    holding_period_days=holding_days, sizing_rule=config["sizing_rule"],
                )
            elif family == "vol_of_vol":
                vol_series = annualized_vol(close, VOL_WINDOW)
                raw_signal = return_over_lookback(vol_series.shift(signal_lag), config["lookback_days"])
                per_ticker_results[ticker] = apply_backtest(
                    raw_signal, close, high, low, volume,
                    vol_window=VOL_WINDOW, target_vol=TARGET_VOL,
                    holding_period_days=holding_days, sizing_rule=config["sizing_rule"],
                )
            else:
                raise ValueError(f"unknown signal_family: {family}")

    gross_by_ticker = {t: r["gross_return"] for t, r in per_ticker_results.items()}

    return pd.DataFrame(gross_by_ticker).mean(axis=1)


def main():
    #laod panel
    panel = pd.read_parquet(PANEL_PATH)
    #remove local timezone again
    panel["date"] = pd.to_datetime(panel["date"]).dt.tz_localize(None)
    # load ticker data
    print("loading per ticker data")
    ticker_data = load_all_ticker_data(panel)
    #build the grid
    configs = build_grid()
    #now do all config daily returns
    print("running all configs, capturing full daily series")

    series_by_config = {}
    for i, config in enumerate(configs):
        series_by_config[config["config_id"]] = run_one_config_series(config, ticker_data)
        
    print("configs done")
    #get sharpes 
    wide = pd.DataFrame(series_by_config)
    daily_sharpe = wide.mean() / wide.std()
    n_obs = wide.notna().sum()
    # get the ID of the config with best sharpe and then the config
    best_config_id = daily_sharpe.idxmax()
    best_config = next(c for c in configs if c["config_id"] == best_config_id)

    #lets do the DSR
    print("Deflated Sharpe Ratio:")
    dsr_result = deflated_sharpe_ratio(daily_sharpe, wide[best_config_id])
    for k, v in dsr_result.items():
        print(f"  {k}: {v}")

    print("HZL RESULTS:")
    hlz_result = hlz_haircut(daily_sharpe, n_obs)
    for k, v in hlz_result.items():
        print(f"  {k}: {v}")

    print("Reality Check")
    rc_result = reality_check_p_value(wide)
    print(f"  p_value: {rc_result['p_value']}")
    print(f"  observed_max_mean: {rc_result['observed_max_mean']}")
    # get best annualized sharpe through DSR result * sqrt(trading days per year)
    best_annualized_sharpe = dsr_result["best_daily_sharpe"] * np.sqrt(TRADING_DAYS_PER_YEAR)
    print("best annualized sharpe: "+ str(best_annualized_sharpe))


if __name__ == "__main__":
    main()
