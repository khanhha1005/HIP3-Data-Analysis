"""
US Treasury Yields + 10Y-2Y Spread Plotter

Pulls FRED yields across the curve: 3M, 2Y, 5Y, 10Y
and plots:
  1) Yield curve time series
  2) 10Y-2Y spread with inversion (spread < 0) highlighted

Data source (FRED series):
  3M  -> DGS3MO
  2Y  -> DGS2
  5Y  -> DGS5
  10Y -> DGS10

Install:
  pip install pandas matplotlib pandas_datareader
"""

import argparse
from datetime import date
import pandas as pd
import matplotlib.pyplot as plt
from pandas_datareader import data as pdr


SERIES = {
    "3M": "DGS3MO",
    "2Y": "DGS2",
    "5Y": "DGS5",
    "10Y": "DGS10",
}


def fetch_treasury_yields(start: str, end: str) -> pd.DataFrame:
    fred_codes = list(SERIES.values())
    df = pdr.DataReader(fred_codes, "fred", start, end)

    # Rename columns to nicer labels (3M/2Y/5Y/10Y)
    reverse_map = {v: k for k, v in SERIES.items()}
    df = df.rename(columns=reverse_map)

    # FRED yields can have missing values on holidays/weekends; forward-fill
    df = df.sort_index().ffill()

    # Keep only rows where we have at least one yield
    df = df.dropna(how="all")
    return df


def plot_yields(df: pd.DataFrame, outpath: str | None = None, show: bool = True):
    plt.figure(figsize=(11, 5.5))
    for col in ["3M", "2Y", "5Y", "10Y"]:
        if col in df.columns:
            plt.plot(df.index, df[col], label=col)

    plt.title("US Treasury Yields (3M, 2Y, 5Y, 10Y)")
    plt.ylabel("Yield (%)")
    plt.xlabel("Date")
    plt.grid(True, alpha=0.3)
    plt.legend()

    # Annotate last values (optional nicety)
    last = df.dropna().iloc[-1]
    txt = "Last: " + ", ".join([f"{k}={last[k]:.2f}%" for k in ["3M", "2Y", "5Y", "10Y"] if k in last])
    plt.gcf().text(0.01, 0.01, txt, fontsize=9)

    if outpath:
        plt.tight_layout()
        plt.savefig(outpath, dpi=200)
    if show:
        plt.show()
    plt.close()


def plot_spread(df: pd.DataFrame, outpath: str | None = None, show: bool = True):
    if "10Y" not in df.columns or "2Y" not in df.columns:
        raise ValueError("Need both 10Y and 2Y yields to compute spread.")

    spread = df["10Y"] - df["2Y"]

    plt.figure(figsize=(11, 5.5))
    plt.plot(spread.index, spread, label="10Y - 2Y Spread")
    plt.axhline(0.0, linewidth=1)

    # Highlight inversions (spread < 0)
    inv = spread < 0
    plt.fill_between(
        spread.index,
        spread.values,
        0.0,
        where=inv.values,
        interpolate=True,
        alpha=0.25,
        label="Inversion (Spread < 0)",
    )

    plt.title("US Treasury 10Y-2Y Spread (Inversion Highlighted)")
    plt.ylabel("Spread (percentage points)")
    plt.xlabel("Date")
    plt.grid(True, alpha=0.3)
    plt.legend()

    # Add quick status note
    last_spread = spread.dropna().iloc[-1]
    status = "INVERTED" if last_spread < 0 else "NORMAL"
    plt.gcf().text(0.01, 0.01, f"Last spread: {last_spread:.2f} pp ({status})", fontsize=9)

    if outpath:
        plt.tight_layout()
        plt.savefig(outpath, dpi=200)
    if show:
        plt.show()
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, default="2015-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=str(date.today()), help="End date (YYYY-MM-DD)")
    parser.add_argument("--weekly", action="store_true", help="Resample to weekly (Fri) for smoother plots")
    parser.add_argument("--save-yields", type=str, default=None, help="Path to save yields plot (png)")
    parser.add_argument("--save-spread", type=str, default=None, help="Path to save spread plot (png)")
    parser.add_argument("--save-csv", type=str, default=None, help="Path to save pulled data as CSV")
    parser.add_argument("--no-show", action="store_true", help="Do not display plots (useful on servers)")
    args = parser.parse_args()

    df = fetch_treasury_yields(args.start, args.end)

    if args.weekly:
        # Friday weekly frequency; last observed value in the week
        df = df.resample("W-FRI").last().ffill()

    # Compute and optionally export
    df["10Y-2Y"] = df["10Y"] - df["2Y"]

    if args.save_csv:
        df.to_csv(args.save_csv, index=True)

    show = not args.no_show

    plot_yields(df[["3M", "2Y", "5Y", "10Y"]], outpath=args.save_yields, show=show)
    plot_spread(df[["2Y", "10Y"]], outpath=args.save_spread, show=show)


if __name__ == "__main__":
    main()
