# v1.4 testing the backtest code on a 12-1 momentum strategy
#
# 12-1  momentum strategy, testing if i get the popular documented results
# you skip the most recent month so the recenct month doesnt influence the strategy so much

import os
import sys

# VSCODE proposed fix to backtest not being reachable directly from here
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

import numpy as np
import pandas as pd
import pytest

from backtest import run_backtest
#same path helper
PANEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "panel.parquet")

# one ticker per asset class bucket (equity/EM equity/bonds/credit/commodities/real estate/FX)

TICKERS = ["SPY", "EEM", "TLT", "HYG", "GLD", "DBC", "VNQ", "UUP"]


TRADING_DAYS_PER_YEAR = 252
SIGNAL_LAG_DAYS = 21   # the most recent month

LOOKBACK_DAYS = TRADING_DAYS_PER_YEAR - SIGNAL_LAG_DAYS
# parameters from the paper:
VOL_WINDOW = 20
TARGET_VOL = 0.10

#get the dataframe
def get_series(panel: pd.DataFrame, ticker: str, field: str) -> pd.Series:
    # keep only the rows for this ticker and this field
    is_this_ticker = panel["ticker"] == ticker
    is_this_field = panel["field"] == field
    series = panel[is_this_ticker & is_this_field]

    # date becomes the index instead of a normal column
    series = series.set_index("date")

    # keep just the value column, now its a clean time series
    series = series["value"]

    # sort oldest to newest
    series = series.sort_index()

    return series


def annualized_sharpe(daily_pnl: pd.Series) -> float:
    return (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return pd.read_parquet(PANEL_PATH)


@pytest.fixture(scope="module")
def backtest_results(panel) -> dict:
    results = {}
    #find Close High Low Vol of each ticker in the smaller universe and run backtest on it
    for ticker in TICKERS:
        close = get_series(panel, ticker, "Close")
        high = get_series(panel, ticker, "High")
        low = get_series(panel, ticker, "Low")
        volume = get_series(panel, ticker, "Volume")
        results[ticker] = run_backtest(
            close, high, low, volume,
            lookback_days=LOOKBACK_DAYS,
            vol_window=VOL_WINDOW,
            target_vol=TARGET_VOL,
            signal_lag_days=SIGNAL_LAG_DAYS,
        )
    return results



def test_portfolio_12_1_momentum_positive_gross_sharpe(backtest_results):
    gross_by_ticker = {}
    for ticker, result in backtest_results.items():
        # pull the gross_return column out of this ticker's result, save it under its name
        gross_by_ticker[ticker] = result["gross_return"]
    #build the "portfolio"
    portfolio = pd.DataFrame(gross_by_ticker).mean(axis=1).dropna()
    # calc the mean return and sharpe
    mean_return = portfolio.mean()
    sharpe = annualized_sharpe(portfolio)

    print(f"PORTFOLIO (equal-weighted, gross): avg daily pnl={mean_return:.6f}, "f"annualized Sharpe={sharpe:.2f}")
