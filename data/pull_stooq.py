# v0 data pull just to confirm if yfinance is reliable
# Stooq clocks API access,cut down to just the 3 tickers.
#SPY, TLT, GLD manually downloaded into src/data/raw

import pandas as pd

TICKERS = ["SPY", "TLT", "GLD"]

FIELDS = ["Open", "High", "Low", "Close", "Volume"]

RAW_DIR = "data/raw"
OUT_PATH = "data/processed/panel_stooq.parquet"


def fetch_one(ticker: str):
    path = f"{RAW_DIR}/{ticker}.csv"
    df = pd.read_csv(path, index_col="Date", parse_dates=["Date"])
    return df


def to_long_format(ticker: str, wide_df: pd.DataFrame):
    #technically the same as yfinance
    #reset indexing and rename Date to date
    wide_df = wide_df.reset_index().rename(columns={"Date": "date"})
    #rechaped the wide table into rows, pairing each field with the respetive field values and keyed by date
    wide_df = pd.melt(wide_df, id_vars=["date"], value_vars=FIELDS, var_name="field", value_name="value")
    # Add a new column "ticker", its value is the same on every row, the ticker argument of the to_long_format fct(name of the ticker)
    wide_df["ticker"] = ticker
    return wide_df



def build_panel(tickers: list) -> pd.DataFrame:
    # flat list now, no buckets — only 3 tickers, just for the cross-check
    frames = []
    for ticker in tickers:
        wide_df = fetch_one(ticker)
        df = to_long_format(ticker, wide_df)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

def main():
    #build the panels, no manifest since we dont need it
    panel = build_panel(TICKERS)
    panel.to_parquet(OUT_PATH)


if __name__ == "__main__":
    main()
