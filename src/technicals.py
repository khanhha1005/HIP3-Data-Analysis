"""
Technical analysis functions for Voyager Dashboard
"""

import math
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute Wilder's RSI."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_macd(series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Compute MACD, Signal, and Histogram."""
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def compute_moving_averages(series: pd.Series) -> Dict[str, pd.Series]:
    """Compute SMA and EMA for 50 and 200 periods."""
    return {
        "sma50": series.rolling(window=50, min_periods=1).mean(),
        "sma200": series.rolling(window=200, min_periods=1).mean(),
        "ema50": series.ewm(span=50, adjust=False).mean(),
        "ema200": series.ewm(span=200, adjust=False).mean(),
    }


def detect_cross_events(sma50: pd.Series, sma200: pd.Series, lookback: int = 20) -> Tuple[bool, bool]:
    """Detect golden/death cross within the last lookback candles."""
    if sma50.empty or sma200.empty:
        return False, False
    diff = sma50 - sma200
    recent = diff.tail(lookback).dropna()
    if len(recent) < 2:
        return False, False
    sign = np.sign(recent)
    golden = False
    death = False
    for prev, cur in zip(sign[:-1], sign[1:]):
        if prev <= 0 and cur > 0:
            golden = True
        if prev >= 0 and cur < 0:
            death = True
    return golden, death


def compute_volatility_24h(close: pd.Series, periods: int = 6) -> float:
    """Compute 24h volatility (assuming 4h candles, 6 periods = 24h)."""
    if len(close) < periods + 1:
        return float("nan")
    last = close.tail(periods + 1)
    logret = np.log(last / last.shift(1)).dropna()
    if len(logret) == 0:
        return float("nan")
    vol = float(logret.tail(periods).std(ddof=0) * math.sqrt(periods))
    return vol


def compute_historical_volatility(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute rolling historical volatility from price data."""
    if df.empty or "close" not in df.columns:
        return pd.DataFrame()
    
    df = df.copy()
    df["returns"] = np.log(df["close"] / df["close"].shift(1))
    # Annualized volatility (assuming 4h candles, 6 per day, ~252 trading days)
    df["hist_vol"] = df["returns"].rolling(window=window).std() * np.sqrt(6 * 252)
    return df[["time", "hist_vol"]].dropna()


def compute_all_technicals(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute all technical indicators for a dataframe."""
    if df.empty:
        return {}

    close = df["close"]
    rsi_series = compute_rsi(close)
    macd_series, signal_series, hist_series = compute_macd(close)
    ma = compute_moving_averages(close)
    golden_cross, death_cross = detect_cross_events(ma["sma50"], ma["sma200"])
    vol_24h = compute_volatility_24h(close)
    
    # Compute historical volatility
    hist_vol_df = compute_historical_volatility(df)

    # Price changes
    def pct_change(n: int) -> float:
        if len(close) <= n:
            return float("nan")
        prev = close.iloc[-1 - n]
        if prev == 0 or pd.isna(prev):
            return float("nan")
        return float((close.iloc[-1] / prev - 1.0) * 100.0)

    # 24h window (6 x 4h candles)
    last6 = df.tail(6)
    high_24h = float(last6["high"].max()) if len(last6) > 0 else float("nan")
    low_24h = float(last6["low"].min()) if len(last6) > 0 else float("nan")
    volume_24h = float(last6["volume"].sum()) if len(last6) > 0 else float("nan")

    return {
        "price": float(close.iloc[-1]) if len(close) > 0 else float("nan"),
        "high_24h": high_24h,
        "low_24h": low_24h,
        "volume_24h": volume_24h,
        "chg_4h": pct_change(1),
        "chg_24h": pct_change(6),
        "chg_7d": pct_change(42),
        "chg_30d": pct_change(180),
        "rsi14": float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else float("nan"),
        "macd": float(macd_series.iloc[-1]) if len(macd_series) > 0 else float("nan"),
        "macd_signal": float(signal_series.iloc[-1]) if len(signal_series) > 0 else float("nan"),
        "macd_hist": float(hist_series.iloc[-1]) if len(hist_series) > 0 else float("nan"),
        "sma50": float(ma["sma50"].iloc[-1]) if len(ma["sma50"]) > 0 else float("nan"),
        "sma200": float(ma["sma200"].iloc[-1]) if len(ma["sma200"]) > 0 else float("nan"),
        "ema50": float(ma["ema50"].iloc[-1]) if len(ma["ema50"]) > 0 else float("nan"),
        "ema200": float(ma["ema200"].iloc[-1]) if len(ma["ema200"]) > 0 else float("nan"),
        "golden_cross": golden_cross,
        "death_cross": death_cross,
        "vol_24h": vol_24h,
        "rsi_series": rsi_series,
        "macd_series": macd_series,
        "signal_series": signal_series,
        "hist_series": hist_series,
        "ma": ma,
        "hist_vol_df": hist_vol_df,
    }

