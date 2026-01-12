#!/usr/bin/env python3
"""
macro_panel.py
RAW macro panel with display labels EXACTLY:
DXY, VIX, S&P 500, Gold, Oil

Data source: Yahoo Finance via yfinance
Install:
  pip install -U yfinance pandas numpy matplotlib

Run:
  python macro_panel.py --period 1mo --interval 1d --save-csv macro.csv --save-fig macro.png
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, Optional, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf


# Display labels (what you want) -> Yahoo tickers (what yfinance needs)
PANEL: Dict[str, str] = {
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "Oil": "CL=F",
}

DISPLAY_ORDER: List[str] = ["DXY", "VIX", "S&P 500", "Gold", "Oil"]


@dataclass(frozen=True)
class FetchConfig:
    period: str = "1mo"
    interval: str = "1d"
    auto_adjust: bool = False


def _pick_close(df: pd.DataFrame) -> pd.Series:
    if "Adj Close" in df.columns:
        return df["Adj Close"].copy()
    if "Close" in df.columns:
        return df["Close"].copy()
    raise ValueError(f"Missing Close/Adj Close columns. Columns={list(df.columns)}")


def fetch_prices_strict(panel: Dict[str, str], cfg: FetchConfig) -> pd.DataFrame:
    """
    Strict fetch: uses exactly the tickers in PANEL (no fallback).
    IMPORTANT: forces columns to be the DISPLAY labels (DXY, VIX, S&P 500, Gold, Oil).
    """
    out: Dict[str, pd.Series] = {}

    for label, ticker in panel.items():
        df = yf.download(
            ticker,
            period=cfg.period,
            interval=cfg.interval,
            auto_adjust=cfg.auto_adjust,
            progress=False,
        )

        if df is None or df.empty:
            raise RuntimeError(
                f"No data for label='{label}' using Yahoo ticker='{ticker}'. "
                f"Try --period 6mo or check Yahoo access."
            )

        s = _pick_close(df)
        if s.dropna().empty:
            raise RuntimeError(
                f"All-NaN series for label='{label}' using Yahoo ticker='{ticker}'."
            )

        # Store by label -> later we force columns = labels
        out[label] = s.astype(float)

    # concat values, then FORCE columns to keys order
    prices = pd.concat(list(out.values()), axis=1).sort_index()
    prices.columns = list(out.keys())  # <<< THIS fixes your empty-columns bug

    # enforce display order
    cols = [c for c in DISPLAY_ORDER if c in prices.columns]
    prices = prices[cols]

    return prices


def compute_snapshot(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Snapshot:
      Last, 1-step, 5-step, 21-step returns (%)
    """
    px = prices.sort_index().ffill()

    # If no columns, return empty snapshot (should not happen now)
    if px.shape[1] == 0:
        return pd.DataFrame(columns=["Last", "Ret_1", "Ret_5", "Ret_21"])

    last = px.iloc[-1]
    r1 = px.pct_change(1).iloc[-1] * 100.0
    r5 = px.pct_change(5).iloc[-1] * 100.0
    r21 = px.pct_change(21).iloc[-1] * 100.0

    snap = pd.DataFrame({"Last": last, "Ret_1": r1, "Ret_5": r5, "Ret_21": r21})
    snap.index.name = "Symbol"
    return snap


def plot_panel_raw(
    prices: pd.DataFrame,
    title: str = "Macro Panel (DXY, VIX, S&P 500, Gold, Oil)",
    save_path: Optional[str] = None,
) -> None:
    """Matplotlib version - kept for CLI compatibility."""
    px = prices.sort_index().copy().ffill()
    px = px.dropna(axis=1, how="all")

    if px.shape[1] == 0:
        raise RuntimeError(
            "Empty price table after cleaning. "
            f"Got columns={list(prices.columns)}; "
            "This usually means Yahoo returned all-NaN."
        )

    cols = [c for c in DISPLAY_ORDER if c in px.columns] + [c for c in px.columns if c not in DISPLAY_ORDER]
    px = px[cols]
    n = len(cols)

    fig, axes = plt.subplots(
        nrows=n,
        ncols=1,
        figsize=(14, max(6, 2.2 * n)),
        sharex=True,
        constrained_layout=True,  # avoids weird crop
    )
    if n == 1:
        axes = [axes]

    for ax, col in zip(axes, cols):
        ax.plot(px.index, px[col])
        ax.grid(True, linewidth=0.4, alpha=0.6)
        ax.set_title(col, loc="left", fontsize=11)
        ax.set_ylabel("")  # keep clean

    fig.suptitle(title, fontsize=13)
    fig.text(0.01, 0.5, "Price/Level", va="center", rotation="vertical")
    axes[-1].set_xlabel("Date")

    # IMPORTANT: don't use bbox_inches="tight" (can produce skinny output)
    if save_path:
        fig.savefig(save_path, dpi=200)
    else:
        plt.show()


def plot_panel_plotly(
    prices: pd.DataFrame,
    title: str = "Macro Panel (DXY, VIX, S&P 500, Gold, Oil)",
) -> go.Figure:
    """
    Beautiful Plotly version of the macro panel with modern styling.
    Returns a Plotly figure object for use in Streamlit.
    """
    px = prices.sort_index().copy().ffill()
    px = px.dropna(axis=1, how="all")

    if px.shape[1] == 0:
        raise RuntimeError(
            "Empty price table after cleaning. "
            f"Got columns={list(prices.columns)}; "
            "This usually means Yahoo returned all-NaN."
        )

    cols = [c for c in DISPLAY_ORDER if c in px.columns] + [c for c in px.columns if c not in DISPLAY_ORDER]
    px = px[cols]
    n = len(cols)

    # Color palette for each indicator
    color_map = {
        "DXY": "#6366f1",      # Indigo (accent)
        "VIX": "#f43f5e",       # Red (volatility)
        "S&P 500": "#10b981",   # Green (equities)
        "Gold": "#f97316",      # Orange (commodity)
        "Oil": "#06b6d4",       # Cyan (energy)
    }

    # Create subplots
    fig = make_subplots(
        rows=n,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=cols,
        row_heights=[1.0] * n,
    )

    # Add traces for each indicator
    for idx, col in enumerate(cols, start=1):
        color = color_map.get(col, "#6366f1")
        
        # Calculate percentage change for fill color
        pct_change = px[col].pct_change().iloc[-1] if len(px) > 1 else 0
        fill_color = "rgba(16, 185, 129, 0.1)" if pct_change >= 0 else "rgba(244, 63, 94, 0.1)"
        
        fig.add_trace(
            go.Scatter(
                x=px.index,
                y=px[col],
                name=col,
                mode="lines",
                line=dict(color=color, width=2.5),
                fill="tozeroy",
                fillcolor=fill_color,
                hovertemplate=f"<b>{col}</b><br>" +
                              "Date: %{x|%Y-%m-%d}<br>" +
                              "Value: %{y:,.2f}<br>" +
                              "<extra></extra>",
            ),
            row=idx,
            col=1,
        )

        # Add grid and styling
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(0, 0, 0, 0.05)",
            showline=True,
            linewidth=1,
            linecolor="rgba(0, 0, 0, 0.1)",
            row=idx,
            col=1,
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(0, 0, 0, 0.05)",
            showline=True,
            linewidth=1,
            linecolor="rgba(0, 0, 0, 0.1)",
            row=idx,
            col=1,
        )

    # Update layout with beautiful styling
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, family="Inter, sans-serif", color="#1e293b"),
            x=0.5,
            xanchor="center",
        ),
        height=max(600, 150 * n),
        template="plotly_white",
        showlegend=False,
        margin=dict(l=60, r=30, t=80, b=50),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace", size=11),
        hovermode="x unified",
    )

    # Update subplot titles styling
    for i in range(n):
        fig.layout.annotations[i].update(
            font=dict(size=13, family="Inter, sans-serif", color="#1e293b", weight=600),
            xanchor="left",
            x=0.02,
        )

    return fig


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--period", default="1mo", help='e.g. "1mo", "6mo", "1y", "2y"')
    p.add_argument("--interval", default="1d", help='e.g. "1d", "1h", "15m"')
    p.add_argument("--save-csv", default=None, help="Save wide prices CSV")
    p.add_argument("--save-fig", default=None, help="Save figure path (png/jpg/pdf)")
    args = p.parse_args()

    cfg = FetchConfig(period=args.period, interval=args.interval, auto_adjust=False)

    prices = fetch_prices_strict(PANEL, cfg)

    print("\nTicker mapping (label -> Yahoo ticker):")
    for label, tkr in PANEL.items():
        print(f"  {label} -> {tkr}")

    print("\nFetched columns:", list(prices.columns))
    print("Rows:", len(prices))

    snap = compute_snapshot(prices).round({"Last": 4, "Ret_1": 2, "Ret_5": 2, "Ret_21": 2})
    print("\n=== Macro Panel Snapshot ===")
    print(snap.to_string())

    if args.save_csv:
        prices.to_csv(args.save_csv)
        print(f"\nSaved prices CSV -> {args.save_csv}")

    plot_panel_raw(prices, save_path=args.save_fig)

    if args.save_fig:
        print(f"Saved figure -> {args.save_fig}")


if __name__ == "__main__":
    main()
