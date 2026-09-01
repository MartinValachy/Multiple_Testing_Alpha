# v2.3: runs every pre registered config from grid.py through the v1/v2 engine, collects in-sample stats per config

import os
import sys
#helper paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
sys.path.insert(0, os.path.dirname(__file__))  # for grid.py, same folder

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed, just save the figure
import matplotlib.pyplot as plt

from grid import build_grid, UNIVERSE_SUBSETS, ALL_TICKERS
from backtest import run_backtest, run_cross_sectional_backtest
from signals import return_over_lookback
from sizing import annualized_vol

PANEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "panel.parquet")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "zoo_raw_stats.parquet")
HIST_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "zoo_sharpe_histogram.png")

# engine settings, not part of the grid
VOL_WINDOW = 20
TARGET_VOL = 0.10
TRADING_DAYS_PER_YEAR = 252
#set holding period days
HOLDING_PERIOD_DAYS = {
    "daily": 1,
    "weekly": 5,
    "monthly": 21,
    "quarterly": 63,
    "semiannual": 126,
}

#load the series
def get_series(panel: pd.DataFrame, ticker: str, field: str) -> pd.Series:
    sub = panel[(panel["ticker"] == ticker) & (panel["field"] == field)]
    #return sorted
    return sub.set_index("date")["value"].sort_index()


def load_all_ticker_data(panel: pd.DataFrame) -> dict:
    #loads Close/High/Low/Volume for each ticker once, insted of at each run 
    data = {}
    for ticker in ALL_TICKERS:
        data[ticker] = {
            "close": get_series(panel, ticker, "Close"),
            "high": get_series(panel, ticker, "High"),
            "low": get_series(panel, ticker, "Low"),
            "volume": get_series(panel, ticker, "Volume")}
    return data

# calc of Annualized sharpe
def annualized_sharpe(daily_pnl: pd.Series) -> float:
    return (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)

# fct of running 1 config of 780, returns a dict

def run_one_config(config: dict, ticker_data: dict) -> dict:
    #set the config singals
    universe = UNIVERSE_SUBSETS[config["universe_subset"]]
    holding_days = HOLDING_PERIOD_DAYS[config["holding_period"]]
    signal_lag = config["signal_lag_days"]
    family = config["signal_family"]
    # for each family, its different, so do simple elifs structure
    if family == "cross_sectional_momentum":
        #load prices, high, low, volume
        prices = {t: ticker_data[t]["close"] for t in universe}
        highs = {t: ticker_data[t]["high"] for t in universe}
        lows = {t: ticker_data[t]["low"] for t in universe}
        volumes = {t: ticker_data[t]["volume"] for t in universe}
        #run the cross sectional backtest, thats absically it
        per_ticker_results = run_cross_sectional_backtest(
            prices, highs, lows, volumes,
            lookback_days=config["lookback_days"], vol_window=VOL_WINDOW,
            target_vol=TARGET_VOL, signal_lag_days=signal_lag,
            holding_period_days=holding_days, sizing_rule=config["sizing_rule"],
        )
    else:
        per_ticker_results = {}
        for ticker in universe:
            #load the values
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
                # bet AGAINST the recent move, not with it
                raw_signal = -return_over_lookback(close, config["lookback_days"])
                from backtest import apply_backtest
                per_ticker_results[ticker] = apply_backtest(
                    raw_signal, close, high, low, volume,
                    vol_window=VOL_WINDOW, target_vol=TARGET_VOL,
                    holding_period_days=holding_days, sizing_rule=config["sizing_rule"],
                )
            elif family == "vol_of_vol":
                # momentum of the REALIZED VOL series, not price
                vol_series = annualized_vol(close, VOL_WINDOW)
                raw_signal = return_over_lookback(vol_series.shift(signal_lag), config["lookback_days"])
                from backtest import apply_backtest
                per_ticker_results[ticker] = apply_backtest(
                    raw_signal, close, high, low, volume,
                    vol_window=VOL_WINDOW, target_vol=TARGET_VOL,
                    holding_period_days=holding_days, sizing_rule=config["sizing_rule"],
                )
            else:
                raise ValueError(f"unknown signal_family: {family}")

    # equalweight the tickers in this universe into one portfolio series
    gross_by_ticker = {t: r["gross_return"] for t, r in per_ticker_results.items()}
    net_by_ticker = {t: r["net_return"] for t, r in per_ticker_results.items()}
    portfolio_gross = pd.DataFrame(gross_by_ticker).mean(axis=1).dropna()
    portfolio_net = pd.DataFrame(net_by_ticker).mean(axis=1).dropna()

    return {
        "n_obs": len(portfolio_gross),
        "gross_mean_daily": portfolio_gross.mean(),
        "gross_sharpe": annualized_sharpe(portfolio_gross),
        "net_mean_daily": portfolio_net.mean(),
        "net_sharpe": annualized_sharpe(portfolio_net),
    }


def main():
    #lode the panel
    panel = pd.read_parquet(PANEL_PATH)
    #strip date of timezone
    panel["date"] = pd.to_datetime(panel["date"]).dt.tz_localize(None)

    print("loading per ticker data now")
    # load all the tickers
    ticker_data = load_all_ticker_data(panel)
    configs = build_grid()
    print("running " + str(len(configs)) +  "configs...")
    # now run all the configs:
    rows = []
    for i, config in enumerate(configs):
        stats = run_one_config(config, ticker_data)
        rows.append({**config, **stats})
    #show the results
    results = pd.DataFrame(rows)
    #save it to OUT_PATH
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    results.to_parquet(OUT_PATH)

    print("saved")
    #make a graph
    plt.figure(figsize=(10, 6))
    plt.hist(results["gross_sharpe"].dropna(), bins=50)
    plt.xlabel("in-sample gross Sharpe")
    plt.ylabel("number of configs")
    plt.title(f"Zoo: in-sample Sharpe distribution across {len(results)} configs")
    plt.savefig(HIST_PATH)
    print("printed the histograph")


if __name__ == "__main__":
    main()
