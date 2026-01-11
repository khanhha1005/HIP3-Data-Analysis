#!/usr/bin/env python3
"""
macro_panel.py
Fetch and visualize macro panel: DXY, VIX, S&P 500, Gold, Oil.

Install:
  pip install yfinance pandas matplotlib
Run:
  python macro_panel.py --period 2y --interval 1d --normalize --save-csv macro.csv --save-fig macro.png
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt

try:
    import yfinance as yf
except ImportError as e:
    raise SystemExit("Missing dependency: yfinance. Install with `pip install yfinance`") from e


ASSETS: Dict[str, str] = {
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "SPX": "^GSPC",
    "GOLD": "GC=F",
    "OIL": "CL=F",
}


@dataclass(frozen=True)
class FetchConfig:
    period: str = "2y"     # e.g., "6mo", "1y", "5y", "max"
    interval: str = "1d"   # e.g., "1d", "1h", "15m"
    auto_adjust: bool = False


def _pick_close(df: pd.DataFrame) -> pd.Series:
    """Pick an available close-like column from yfinance output."""
    for col in ["Adj Close", "Close"]:
        if col in df.columns:
            return df[col].copy()
    raise ValueError(f"Cannot find Close/Adj Close in columns: {list(df.columns)}")


def fetch_prices(
    assets: Dict[str, str],
    cfg: FetchConfig,
) -> pd.DataFrame:
    """
    Returns a wide DataFrame of close prices with columns=asset keys (DXY, VIX, ...).
    """
    tickers = list(assets.values())
    raw = yf.download(
        tickers=tickers,
        period=cfg.period,
        interval=cfg.interval,
        auto_adjust=cfg.auto_adjust,
        group_by="ticker",
        threads=True,
        progress=False,
    )

    if raw.empty:
        raise RuntimeError("No data returned. Try a different period/interval or check connectivity.")

    out = pd.DataFrame(index=raw.index)

    # yfinance returns:
    # - MultiIndex columns when multiple tickers
    # - Single-level columns when one ticker
    if isinstance(raw.columns, pd.MultiIndex):
        # Level0: ticker, Level1: OHLCV fields
        for name, tkr in assets.items():
            if tkr not in raw.columns.get_level_values(0):
                continue
            sub = raw[tkr].dropna(how="all")
            if sub.empty:
                continue
            out[name] = _pick_close(sub)
    else:
        # Single ticker case
        only_name = next(iter(assets.keys()))
        out[only_name] = _pick_close(raw)

    out = out.sort_index()
    out = out.dropna(how="all")
    return out


def compute_returns(prices: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Returns:
      - summary table with last, 1D, 1W, 1M % returns
      - last row of prices
    """
    px = prices.dropna(how="all")
    last = px.ffill().iloc[-1]

    # Use row shifts for returns (works for daily; for intraday you still get “1 step”, “5 steps”, “21 steps”)
    r1 = px.pct_change(1).iloc[-1] * 100.0
    r5 = px.pct_change(5).iloc[-1] * 100.0
    r21 = px.pct_change(21).iloc[-1] * 100.0

    summary = pd.DataFrame(
        {
            "Last": last,
            "Ret_1": r1,
            "Ret_5": r5,
            "Ret_21": r21,
        }
    )
    return summary, last


def plot_panel(
    prices: pd.DataFrame,
    normalize: bool = True,
    title: str = "Macro Panel (DXY, VIX, S&P 500, Gold, Oil)",
    save_path: Optional[str] = None,
) -> None:
    """
    5-row panel plot, one asset per axis.
    """
    px = prices.dropna(how="all").ffill()

    if normalize:
        base = px.iloc[0]
        px_plot = (px / base) * 100.0
        ylabel = "Index (Start=100)"
    else:
        px_plot = px
        ylabel = "Price/Level"

    n = px_plot.shape[1]
    fig, axes = plt.subplots(nrows=n, ncols=1, figsize=(12, 2.3 * n), sharex=True)

    if n == 1:
        axes = [axes]

    for ax, col in zip(axes, px_plot.columns):
        ax.plot(px_plot.index, px_plot[col])
        ax.set_ylabel(col)
        ax.grid(True, linewidth=0.4, alpha=0.6)

    axes[0].set_title(title)
    axes[-1].set_xlabel("Date")
    fig.supylabel(ylabel)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches="tight")
    else:
        plt.show()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--period", default="2y", help='e.g. "6mo", "1y", "2y", "5y", "max"')
    p.add_argument("--interval", default="1d", help='e.g. "1d", "1h", "15m"')
    p.add_argument("--no-normalize", action="store_true", help="Plot raw levels instead of Start=100")
    p.add_argument("--save-csv", default=None, help="Path to save wide prices CSV")
    p.add_argument("--save-fig", default=None, help="Path to save figure (png/jpg/pdf)")
    args = p.parse_args()

    cfg = FetchConfig(period=args.period, interval=args.interval, auto_adjust=False)

    prices = fetch_prices(ASSETS, cfg)

    summary, _ = compute_returns(prices)
    summary = summary.round({"Last": 4, "Ret_1": 2, "Ret_5": 2, "Ret_21": 2})

    print("\n=== Macro Panel Snapshot ===")
    print(summary.to_string())

    if args.save_csv:
        prices.to_csv(args.save_csv)
        print(f"\nSaved prices CSV -> {args.save_csv}")

    plot_panel(
        prices=prices,
        normalize=(not args.no_normalize),
        save_path=args.save_fig,
    )
    if args.save_fig:
        print(f"Saved figure -> {args.save_fig}")


if __name__ == "__main__":
    main()
