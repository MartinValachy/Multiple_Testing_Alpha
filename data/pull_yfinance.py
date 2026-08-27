#Z1 v0 Data Pull form yfinance
#Pull all 44 tickers, as much history as possible, in one long format.
#columns will be: date, ticker, field, value.
#fields are: Open, High, Low, Close, Adj Close, Volume

import pandas as pd
import yfinance as yf

# The tickers, basically, you can switch these if you want

TICKERS = {
    "Equity": ["SPY", "QQQ", "IWM", "MDY", "EFA", "EEM", "VGK", "EWJ", "EWZ","EWY", "EWA", "EWC", "EWG", "EWU", "EWH", "VT"],
    "Sectors": ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"],
    "Fixed income": ["TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "AGG", "EMB", "BNDX"],
    "Commodities": ["GLD", "SLV", "DBC", "USO", "DBA", "PDBC"],
    "Real estate": ["VNQ", "IYR"],
    "FX": ["UUP", "FXE"],
}

FIELDS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
#paths to folders and files
OUT_PATH = "data/processed/panel_yfinance.parquet"
MANIFEST_PATH = "data/MANIFEST.md"

# fetch_one will pull the whole history of one ticker through yfinance
def fetch_one(ticker: str):
    df = yf.Ticker(ticker).history(period="max", auto_adjust=False)
    return df


def to_long_format(ticker: str, wide_df: pd.DataFrame):
    #reset indexing and rename Date to date
    wide_df = wide_df.reset_index().rename(columns={"Date": "date"})
    #rechaped the wide table into rows, pairing each field with the respetive field values and keyed by date
    wide_df = pd.melt(wide_df, id_vars=["date"], value_vars=FIELDS, var_name="field", value_name="value")
    # Add a new column "ticker", its value is the same on every row, the ticker argument of the to_long_format fct(name of the ticker)
    wide_df["ticker"] = ticker
    return wide_df

def build_panel(tickers_by_bucket: dict):
    frames = []
    for bucket, tickers in tickers_by_bucket.items():
        for ticker in tickers:
            wide_df = fetch_one(ticker)
            df = to_long_format(ticker, wide_df)
            frames.append(df)

    return pd.concat(frames, ignore_index=True)


def pct_nan(values: pd.Series) -> float:
    # how many values are missing (NaN)?
    num_missing = values.isna().sum()
    # how many values are there in total?
    num_total = len(values)
    # what fraction is missing, as a percentage?
    return 100 * num_missing / num_total


def write_manifest(panel: pd.DataFrame, tickers_by_bucket: dict, path: str) -> None:
    stats = panel.groupby("ticker").agg(row_count=("value", "size"),date_min=("date", "min"),date_max=("date", "max"),pct_nan=("value", pct_nan))
    #hardcode tha source
    stats["source"] = "yfinance"
    #reset index again
    stats = stats.reset_index()

    # turn the stats table into one big markdown-formatted string
    table_text = stats.to_markdown(index=False, floatfmt=".2f")

    # build the full file content: a heading, then the table, then a newline
    file_content = "# Z1 Data Manifest\n\n" + table_text + "\n"

    # open the file at `path` in write mode
    f = open(path, "w")
    # write everything to it
    f.write(file_content)
    # close the file so the changes save
    f.close()


def main():
    #build the panels
    panel = build_panel(TICKERS)
    #save the panel
    panel.to_parquet(OUT_PATH)
    #write the manifest, save it to src/data
    write_manifest(panel, TICKERS, MANIFEST_PATH)

if __name__ == "__main__":
    main()
    
