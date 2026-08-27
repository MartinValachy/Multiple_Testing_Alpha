# v0 clean.py
#takes the raw yfiannce data that i pulled, and cleans it. SHould be already cleaned as in notebook, but jsut to make sure
# no duplictes, no missing days as per NYSE calendar no backfilling

import pandas as pd
import pandas_market_calendars as mcal

#paths
RAW_PATH = "data/processed/panel_yfinance.parquet"
OUT_PATH = "data/processed/panel.parquet"

# load the yfinance panel and remove the timezone from "date"
def load_raw_panel(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df


# every row, check if (date, ticker, field) combination appears somewhere
def find_duplicates(panel: pd.DataFrame) -> pd.DataFrame:
    #there is a nice function for that .duplicated
    is_a_duplicate = panel.duplicated(subset=["date", "ticker", "field"], keep=False)
    # keep only the rows where that was True, so we can look at them
    duplicate_rows = panel[is_a_duplicate]
    return duplicate_rows


def drop_duplicates(panel: pd.DataFrame):
    #there is again a nice function for that
    return panel.drop_duplicates(subset=["date", "ticker", "field"])


def check_calendar_gaps(panel: pd.DataFrame, calendar) -> pd.DataFrame:
    rows = []
    #same as in the notebook
    for ticker in panel["ticker"].unique():
        # step 1: every date i actually have for this ticker
        ticker_rows = panel[panel["ticker"] == ticker]
        actual_dates = set(ticker_rows["date"].dt.date)

        # step 2: the first and last date i have data for
        first_date = min(actual_dates)
        last_date = max(actual_dates)

        # step 3: ask the NYSE calendar which days SHOULD have had trading in that same window
        schedule = calendar.schedule(start_date=first_date, end_date=last_date)
        expected_dates = set(schedule.index.date)

        # step 4: dates that should be there but are missing from my data
        missing_dates = expected_dates - actual_dates

        rows.append({"ticker": ticker, "num_missing_days": len(missing_dates)})

    return pd.DataFrame(rows)

#just save the panel that is given
def write_clean_panel(panel: pd.DataFrame, path: str):
  panel.to_parquet(path)


def main():
    #load the panel form yfinance
    panel = load_raw_panel(RAW_PATH)
    #find if there are duplicates
    dupes = find_duplicates(panel)
    print("duplicates found:"+ str(len(dupes)))
    # if theres more, print all duplicates
    if len(dupes) > 0:
        print(dupes)
    # aaand drop them 
    panel = drop_duplicates(panel)
    #load the calendar, check the gaps and print a table of ticker descending with the number of missing days
    # should be all 0 as found in the notebook 
    nyse = mcal.get_calendar("NYSE")
    gaps = check_calendar_gaps(panel, nyse)
    print(gaps.sort_values("num_missing_days", ascending=False))
    #and finally save it to data/processed
    write_clean_panel(panel, OUT_PATH)


if __name__ == "__main__":
    main()
