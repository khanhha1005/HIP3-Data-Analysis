"""
Options functions for Voyager Dashboard
"""

import warnings
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_options_data(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch options data from yfinance with robust error handling."""
    try:
        warnings.filterwarnings("ignore")
        
        tk = yf.Ticker(ticker)
        
        # Try to get options expirations
        try:
            exps = tk.options
        except Exception:
            return None

        if not exps:
            return None

        # Get nearest expiry
        nearest_expiry = exps[0]
        
        try:
            opt_chain = tk.option_chain(nearest_expiry)
        except Exception:
            return None

        calls = opt_chain.calls.copy()
        puts = opt_chain.puts.copy()
        
        if calls.empty and puts.empty:
            return None

        # Get current price - try multiple methods
        spot = 0
        try:
            hist = tk.history(period="1d")
            if not hist.empty:
                spot = float(hist["Close"].iloc[-1])
        except Exception:
            pass
        
        if spot == 0:
            try:
                info = tk.info
                spot = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0
            except Exception:
                pass
        
        if spot == 0:
            if not calls.empty:
                spot = float(calls["strike"].median())

        # Calculate max pain
        strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
        if not strikes:
            return None
            
        max_pain_strike = strikes[len(strikes) // 2]
        min_pain = float("inf")

        for strike in strikes:
            call_pain = 0
            put_pain = 0
            
            itm_calls = calls[calls["strike"] < strike]
            if not itm_calls.empty:
                call_pain = ((strike - itm_calls["strike"]) * itm_calls["openInterest"].fillna(0)).sum()
            
            itm_puts = puts[puts["strike"] > strike]
            if not itm_puts.empty:
                put_pain = ((itm_puts["strike"] - strike) * itm_puts["openInterest"].fillna(0)).sum()
            
            total_pain = call_pain + put_pain
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = strike

        # ATM IV (approximate)
        atm_iv = 0
        if spot > 0:
            atm_calls = calls[abs(calls["strike"] - spot) < spot * 0.05]
            if not atm_calls.empty:
                atm_iv = float(atm_calls["impliedVolatility"].fillna(0).mean())

        # 25-delta skew (simplified) - calculate put and call IV separately
        put_iv = 0
        call_iv = 0
        skew = 0
        if spot > 0:
            otm_puts = puts[puts["strike"] < spot * 0.95]
            otm_calls = calls[calls["strike"] > spot * 1.05]
            put_iv = float(otm_puts["impliedVolatility"].fillna(0).mean()) if not otm_puts.empty else 0
            call_iv = float(otm_calls["impliedVolatility"].fillna(0).mean()) if not otm_calls.empty else 0
            skew = put_iv - call_iv

        return {
            "ticker": ticker,
            "expiry": nearest_expiry,
            "spot": spot,
            "max_pain": max_pain_strike,
            "atm_iv": atm_iv,
            "put_iv": put_iv,
            "call_iv": call_iv,
            "skew_25d": skew,
            "calls": calls,
            "puts": puts,
        }

    except Exception as e:
        return None

