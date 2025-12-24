"""
API functions for fetching data from Hyperliquid
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import pandas as pd
import requests
import streamlit as st

from src.config import API_URL


@st.cache_data(ttl=300)
def post_info(payload: Dict[str, Any]) -> Any:
    """POST to Hyperliquid /info with caching."""
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def discover_assets() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Discover all assets via metaAndAssetCtxs."""
    payload = {"type": "metaAndAssetCtxs"}
    data = post_info(payload)

    if data is None:
        return {}, {}

    if isinstance(data, list) and len(data) >= 2 and isinstance(data[0], dict):
        meta = data[0]
        asset_ctxs_raw = data[1]
    elif isinstance(data, dict):
        meta = data.get("meta", data)
        asset_ctxs_raw = data.get("assetCtxs", data.get("contexts", []))
    else:
        return {}, {}

    universe = meta.get("universe", [])

    assets_by_coin = {}
    for u in universe:
        coin = u.get("name") or u.get("coin")
        if coin:
            assets_by_coin[coin] = u

    ctxs_by_coin = {}
    if isinstance(asset_ctxs_raw, list) and len(asset_ctxs_raw) == len(universe):
        for u, ctx in zip(universe, asset_ctxs_raw):
            coin = u.get("name") or u.get("coin")
            if coin and isinstance(ctx, dict):
                ctxs_by_coin[coin] = ctx

    return assets_by_coin, ctxs_by_coin


@st.cache_data(ttl=60)
def fetch_candles(coin: str, interval: str, days: int) -> pd.DataFrame:
    """Fetch candle data from Hyperliquid."""
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)

    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": int(start_dt.timestamp() * 1000),
            "endTime": int(end_dt.timestamp() * 1000),
        },
    }

    data = post_info(payload)
    if not data or not isinstance(data, list):
        return pd.DataFrame()

    field_map = {
        "t": "startTimeMs",
        "T": "endTimeMs",
        "s": "symbol",
        "i": "interval",
        "o": "open",
        "c": "close",
        "h": "high",
        "l": "low",
        "v": "volume",
        "n": "numTrades",
    }

    rows = []
    for r in data:
        full_row = {field_map[k]: r.get(k) for k in field_map.keys() if k in r}
        rows.append(full_row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["startTimeMs"], unit="ms", utc=True)
    df = df.sort_values("time").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume", "numTrades"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_funding_history_uncached(coin: str, days: int = 7) -> pd.DataFrame:
    """Fetch funding history from Hyperliquid without caching to ensure fresh data per coin."""
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)

    payload = {
        "type": "fundingHistory",
        "coin": coin,
        "startTime": int(start_dt.timestamp() * 1000),
        "endTime": int(end_dt.timestamp() * 1000),
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return pd.DataFrame()
    
    if not data or not isinstance(data, list):
        return pd.DataFrame()

    rows = []
    for row in data:
        try:
            ts = datetime.fromtimestamp(int(row["time"]) / 1000.0, tz=timezone.utc)
            fr = float(row.get("fundingRate", 0.0))
            rows.append({"time": ts, "funding_rate": fr, "coin": coin})
        except (KeyError, TypeError, ValueError):
            continue

    df = pd.DataFrame(rows)
    return df


@st.cache_data(ttl=120, show_spinner=False)
def fetch_funding_history(coin: str, days: int = 7) -> pd.DataFrame:
    """Fetch funding history with proper per-coin caching."""
    return fetch_funding_history_uncached(coin, days)

