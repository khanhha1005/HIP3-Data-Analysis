"""
Voyager HIP-3 Equity Perps Dashboard
Main entry point for Streamlit application
"""

import json
import math
import re
import time
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
import numpy as np

from src.api import discover_assets, fetch_candles, fetch_funding_history
from src.charts import (
    create_funding_chart,
    create_iv_smile_chart,
    create_macd_chart,
    create_price_chart,
    create_rsi_chart,
    create_skew_pie,
    create_volume_chart,
)
from src.config import SYMBOLS
from src.data_classes import DerivativesMetrics
from src.derivatives import compute_derivatives_metrics
from src.options import fetch_options_data
from src.technicals import compute_all_technicals
from src.utils import extract_ticker, format_currency, format_pct


def main():
    st.set_page_config(
        page_title="Voyager HIP-3 Dashboard",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Enhanced Custom CSS
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        
        :root {
            --bg-primary: #f8fafc;
            --bg-secondary: #f1f5f9;
            --bg-card: rgba(255, 255, 255, 0.8);
            --bg-glass: rgba(255, 255, 255, 0.9);
            --border-color: rgba(0, 0, 0, 0.08);
            --accent: #6366f1;
            --accent-glow: #818cf8;
            --accent-purple: #a855f7;
            --accent-pink: #ec4899;
            --green: #10b981;
            --red: #f43f5e;
            --blue: #3b82f6;
            --purple: #8b5cf6;
            --cyan: #06b6d4;
            --text: #1e293b;
            --text-muted: #64748b;
            --shadow-glow: 0 8px 32px rgba(99, 102, 241, 0.15);
        }
        
        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #e2e8f0 100%);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
        }
        
        /* Glassmorphism Header - Light Theme */
        .main-header {
            text-align: center;
            padding: 50px 30px;
            margin: 20px 0 40px 0;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 32px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), 
                        inset 0 1px 0 rgba(255, 255, 255, 0.9);
            position: relative;
            overflow: hidden;
        }
        
        .main-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: -50%;
            width: 200%;
            height: 100%;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(99, 102, 241, 0.1), 
                transparent
            );
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0% { left: -50%; }
            100% { left: 50%; }
        }
        
        .main-title {
            font-family: 'Inter', sans-serif;
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradient-shift 4s ease infinite;
            margin-bottom: 16px;
            letter-spacing: -2px;
            position: relative;
            z-index: 1;
        }
        
        @keyframes gradient-shift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .subtitle {
            color: var(--text-muted);
            font-size: 1.15rem;
            font-family: 'Inter', sans-serif;
            font-weight: 400;
            letter-spacing: 0.5px;
            position: relative;
            z-index: 1;
        }
        
        /* Glassmorphism Metrics - Light Theme */
        div[data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text);
        }
        
        div[data-testid="stMetricLabel"] {
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stMetric {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 24px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08),
                        inset 0 1px 0 rgba(255, 255, 255, 0.9);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .stMetric::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(99, 102, 241, 0.1), 
                transparent
            );
            transition: left 0.5s;
        }
        
        .stMetric:hover {
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 40px rgba(99, 102, 241, 0.2),
                        inset 0 1px 0 rgba(255, 255, 255, 1);
            border-color: rgba(99, 102, 241, 0.3);
        }
        
        .stMetric:hover::before {
            left: 100%;
        }
        
        /* Modern Tab styling - Light Theme */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 8px;
            border: 1px solid rgba(0, 0, 0, 0.08);
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: 14px;
            padding: 16px 32px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            color: var(--text-muted);
            font-size: 0.95rem;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(99, 102, 241, 0.1);
            color: var(--accent);
            transform: translateY(-2px);
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%) !important;
            color: var(--text) !important;
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.2),
                        inset 0 1px 0 rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        
        /* Glass Card styling - Light Theme */
        .info-card {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 32px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            margin-bottom: 28px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08),
                        inset 0 1px 0 rgba(255, 255, 255, 0.9);
        }
        
        .card-title {
            font-family: 'Inter', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        /* Glass Sidebar - Light Theme */
        section[data-testid="stSidebar"] {
            background: rgba(248, 250, 252, 0.95) !important;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-right: 1px solid rgba(0, 0, 0, 0.08);
        }
        
        section[data-testid="stSidebar"] .stMarkdown h3 {
            font-family: 'Inter', sans-serif;
            color: var(--accent);
            font-weight: 700;
        }
        
        /* Glass Dataframe - Light Theme */
        .stDataFrame {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }
        
        /* Glass Expander - Light Theme */
        .streamlit-expanderHeader {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            font-family: 'Inter', sans-serif;
            border: 1px solid rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
        }
        
        .streamlit-expanderHeader:hover {
            background: rgba(255, 255, 255, 1);
            border-color: rgba(99, 102, 241, 0.3);
        }
        
        /* Modern Scrollbar - Light Theme */
        ::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(241, 245, 249, 0.8);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-purple) 100%);
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, var(--accent-glow) 0%, var(--accent-purple) 100%);
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
        }
        
        /* Glass Alert boxes - Light Theme */
        .stSuccess, .stInfo, .stWarning, .stError {
            border-radius: 20px;
            font-family: 'Inter', sans-serif;
            border: 1px solid rgba(0, 0, 0, 0.08);
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.9);
        }
        
        /* Typography */
        h1, h2, h3, h4 {
            font-family: 'Inter', sans-serif !important;
            color: var(--text) !important;
        }
        
        code {
            font-family: 'JetBrains Mono', monospace !important;
            background: rgba(99, 102, 241, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            color: var(--accent);
        }
        
        /* Main content area */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Selection and inputs - Light Theme */
        .stSelectbox, .stMultiselect, .stSlider {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 12px;
        }
        
        /* Button styling - Light Theme */
        .stButton > button {
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-purple) 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(99, 102, 241, 0.5);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header
    st.markdown(
        """
        <div class="main-header">
            <div class="main-title">🚀 VOYAGER</div>
            <div class="subtitle">HIP-3 Perpetuals Analytics Dashboard</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚡ Control Panel")

        # Default to popular symbols for better performance
        default_symbols = ["xyz:AAPL", "xyz:TSLA", "xyz:NVDA", "xyz:META", "xyz:GOOGL", "xyz:AMZN", "xyz:MSFT", "xyz:NFLX"]
        
        # Symbol selection with search
        selected_symbols = st.multiselect(
            "🎯 Select Symbols",
            options=SYMBOLS,
            default=default_symbols,
            help="Choose which symbols to track. Use search to filter by name.",
        )
        
        # Show symbol count and quick info
        if selected_symbols:
            st.caption(f"📈 {len(selected_symbols)} symbol(s) selected")
            # Group by prefix
            xyz_count = len([s for s in selected_symbols if s.startswith("xyz:")])
            flx_count = len([s for s in selected_symbols if s.startswith("flx:")])
            vntl_count = len([s for s in selected_symbols if s.startswith("vntl:")])
            if xyz_count > 0 or flx_count > 0 or vntl_count > 0:
                groups = []
                if xyz_count > 0:
                    groups.append(f"xyz: {xyz_count}")
                if flx_count > 0:
                    groups.append(f"flx: {flx_count}")
                if vntl_count > 0:
                    groups.append(f"vntl: {vntl_count}")
                st.caption(f"📊 {', '.join(groups)}")

        # Default lookback period (removed from UI)
        lookback_days = 30

        st.markdown("---")
        
        auto_refresh = st.checkbox("🔄 Auto-refresh (5 min)", value=False)
        if auto_refresh:
            time.sleep(300)
            st.rerun()

        st.markdown("---")
        st.markdown("### 📡 Data Freshness")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Funding**")
            st.caption("⏱️ 1 hour")
            st.markdown("**Options**")
            st.caption("⏱️ 6 hours")
        with col2:
            st.markdown("**Price**")
            st.caption("⏱️ 4 hours")

        st.markdown("---")
        
        # ETF Settings
        st.markdown("### 📊 ETF Settings")
        etf_period = st.selectbox("ETF Time Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3, key="etf_period")
        
        st.markdown("---")
        
        # Polymarket Settings
        st.markdown("### 🎯 Polymarket Settings")
        polymarket_year = st.number_input("Year", min_value=2024, max_value=2030, value=2026, key="polymarket_year")
        st.caption("Predictions will be fetched for all selected symbols above")
        
        st.markdown("---")
        
        st.markdown(
            f"<small style='color: #71717a;'>Last sync: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC</small>",
            unsafe_allow_html=True,
        )

    if not selected_symbols:
        st.warning("⚠️ Please select at least one symbol from the sidebar.")
        st.info("💡 Tip: Start with a few symbols for faster loading, then add more as needed.")
        return

    # Fetch data with progress tracking
    assets_by_coin, ctxs_by_coin = discover_assets()
    
    all_data = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_symbols = len(selected_symbols)
    for idx, symbol in enumerate(selected_symbols):
        ticker = extract_ticker(symbol)
        progress = (idx + 1) / total_symbols
        progress_bar.progress(progress)
        status_text.text(f"🔄 Loading {ticker}... ({idx + 1}/{total_symbols})")
        
        try:
            df = fetch_candles(symbol, "4h", lookback_days)
            
            # Fetch funding history individually for each symbol
            funding_df = fetch_funding_history(symbol, days=7)
            
            technicals = compute_all_technicals(df) if not df.empty else {}
            deriv_metrics = compute_derivatives_metrics(symbol, funding_df)
            options_data = fetch_options_data(ticker)

            all_data[symbol] = {
                "ticker": ticker,
                "df": df,
                "funding_df": funding_df,
                "technicals": technicals,
                "deriv_metrics": deriv_metrics,
                "options_data": options_data,
            }
        except Exception as e:
            st.warning(f"⚠️ Error loading {ticker}: {str(e)}")
            # Continue with other symbols even if one fails
            all_data[symbol] = {
                "ticker": ticker,
                "df": pd.DataFrame(),
                "funding_df": pd.DataFrame(),
                "technicals": {},
                "deriv_metrics": DerivativesMetrics(
                    ticker=ticker,
                    coin=symbol,
                    latest_funding_annualized=None,
                    mean_funding_annualized=None,
                    max_funding_annualized=None,
                    min_funding_annualized=None,
                    funding_comment="Error loading data.",
                    estimated_long_ratio=0.5,
                    estimated_short_ratio=0.5,
                ),
                "options_data": {},
            }
    
    progress_bar.empty()
    status_text.empty()

    # Main content tabs
    tab_overview, tab_technicals, tab_derivatives, tab_options, tab_etf, tab_polymarket = st.tabs(
        ["📈 Market Snapshot", "📊 Technical Analysis", "🔥 Derivatives Intel", "📉 Options Analytics", "📊 ETF Flow Analysis", "🎯 Polymarket Predictions"]
    )

    # =============================================================================
    # TAB 1: MARKET SNAPSHOT
    # =============================================================================
    with tab_overview:
        st.markdown("### 📈 Market Snapshot")
        st.caption("Real-time prices, volume, and price changes across multiple timeframes")

        # Summary cards
        cols = st.columns(len(selected_symbols))
        for i, (symbol, data) in enumerate(all_data.items()):
            tech = data["technicals"]
            if tech:
                with cols[i]:
                    price = tech.get("price", float("nan"))
                    chg_24h = tech.get("chg_24h", float("nan"))
                    
                    trend_icon = "🟢" if chg_24h > 0 else ("🔴" if chg_24h < 0 else "⚪")
                    st.markdown(f"#### {trend_icon} {data['ticker']}")
                    st.metric(
                        "Price",
                        format_currency(price),
                        delta=format_pct(chg_24h) if not math.isnan(chg_24h) else None,
                        delta_color="normal" if chg_24h >= 0 else "inverse",
                    )

        st.markdown("---")

        # Detailed view per symbol
        for symbol, data in all_data.items():
            ticker = data["ticker"]
            tech = data["technicals"]
            df = data["df"]

            if not tech or df.empty:
                st.warning(f"No data available for {symbol}")
                continue

            st.markdown(f"### {ticker}")

            col1, col2, col3, col4, col5, col6 = st.columns(6)

            with col1:
                st.metric("💰 Price", format_currency(tech.get("price", float("nan"))))
            with col2:
                st.metric("📈 24h High", format_currency(tech.get("high_24h", float("nan"))))
            with col3:
                st.metric("📉 24h Low", format_currency(tech.get("low_24h", float("nan"))))
            with col4:
                st.metric("📊 Volume", f"{tech.get('volume_24h', 0):,.0f}")
            with col5:
                vol = tech.get("vol_24h", float("nan"))
                st.metric("⚡ Volatility", f"{vol:.2%}" if not math.isnan(vol) else "N/A")
            with col6:
                chg_7d = tech.get("chg_7d", float("nan"))
                st.metric("📅 7d Change", format_pct(chg_7d))

            if "ma" in tech:
                st.plotly_chart(create_price_chart(df, ticker, tech["ma"]), use_container_width=True, key=f"price_{ticker}")

            st.markdown("---")

    # =============================================================================
    # TAB 2: TECHNICAL ANALYSIS
    # =============================================================================
    with tab_technicals:
        st.markdown("### 📊 Technical Analysis")
        st.caption("RSI, MACD, Moving Averages, and trend indicators")

        for symbol, data in all_data.items():
            ticker = data["ticker"]
            tech = data["technicals"]
            df = data["df"]

            if not tech or df.empty:
                continue

            st.markdown(f"### {ticker}")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                rsi = tech.get("rsi14", float("nan"))
                rsi_color = "🔴" if rsi > 70 else ("🟢" if rsi < 30 else "⚪")
                st.metric(f"{rsi_color} RSI (14)", f"{rsi:.1f}" if not math.isnan(rsi) else "N/A")

            with col2:
                macd_hist = tech.get("macd_hist", float("nan"))
                macd_color = "🟢" if macd_hist > 0 else "🔴"
                st.metric(f"{macd_color} MACD", f"{macd_hist:.4f}" if not math.isnan(macd_hist) else "N/A")

            with col3:
                st.metric("📊 SMA 50", format_currency(tech.get("sma50", float("nan"))))

            with col4:
                st.metric("📊 SMA 200", format_currency(tech.get("sma200", float("nan"))))

            with col5:
                if tech.get("golden_cross"):
                    st.success("🌟 Golden Cross!")
                elif tech.get("death_cross"):
                    st.error("💀 Death Cross!")
                else:
                    st.info("📊 No Cross Signal")

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                if "rsi_series" in tech:
                    st.markdown("#### RSI (Relative Strength Index) Chart")
                    st.caption(
                        "The **RSI(14)** is a momentum oscillator that measures the speed and magnitude of price movements on a scale of 0-100. "
                        "The **red dashed line at 70** indicates **Overbought** conditions (potential sell signal), while the **green dashed line at 30** "
                        "indicates **Oversold** conditions (potential buy signal). The **grey dotted line at 50** represents the neutral midpoint. "
                        "When RSI crosses above 70, the asset may be overbought and due for a pullback. When RSI falls below 30, it may be oversold "
                        "and due for a bounce. Divergences between RSI and price can signal potential trend reversals."
                    )
                    st.plotly_chart(create_rsi_chart(df, tech["rsi_series"], ticker), use_container_width=True, key=f"rsi_{ticker}")

            with chart_col2:
                if "macd_series" in tech:
                    st.plotly_chart(
                        create_macd_chart(df, tech["macd_series"], tech["signal_series"], tech["hist_series"], ticker),
                        use_container_width=True,
                        key=f"macd_{ticker}",
                    )

            st.markdown("#### Buy/Sell Volume Chart")
            st.caption(
                "This chart displays daily trading volume with two bars per day: **green bars** represent buying volume "
                "(when close price ≥ open price) and **red bars** represent selling volume (when close price < open price). "
                "The height of each bar indicates the volume magnitude. This visualization helps identify periods of "
                "accumulation (green dominance) versus distribution (red dominance), and can signal potential trend reversals "
                "or continuation patterns based on volume-price relationships."
            )
            st.plotly_chart(create_volume_chart(df, ticker), use_container_width=True, key=f"volume_{ticker}")
            st.markdown("---")

    # =============================================================================
    # TAB 3: DERIVATIVES INTELLIGENCE
    # =============================================================================
    with tab_derivatives:
        st.markdown("### 🔥 Derivatives Intelligence")
        st.caption("Funding rates and market positioning derived from perpetual futures data")

        # Summary cards with pie charts
        cols = st.columns(len(selected_symbols))
        for i, (symbol, data) in enumerate(all_data.items()):
            dm = data["deriv_metrics"]
            with cols[i]:
                st.markdown(f"#### {dm.ticker}")
                
                # Funding rate metric - calculated from historical average, annualized
                if dm.latest_funding_annualized is not None:
                    funding_val = dm.latest_funding_annualized
                    funding_color = "🟢" if funding_val > 0.05 else ("🔴" if funding_val < -0.05 else "⚪")
                    st.metric(
                        f"{funding_color} Funding (7d Avg Ann.)",
                        f"{funding_val:.1%}",
                    )
                else:
                    st.metric("Funding (7d Avg)", "N/A")

        st.markdown("---")

        # Interpretation guides
        with st.expander("📖 Funding Rate Guide", expanded=False):
            st.markdown(
                """
                | Funding | Interpretation |
                |---------|----------------|
                | **> +50%** | Extremely crowded longs - correction risk |
                | **+10% to +50%** | Bullish positioning |
                | **-10% to +10%** | Neutral / balanced |
                | **-50% to -10%** | Bearish skew |
                | **< -50%** | Crowded shorts - squeeze risk |
                """
            )

        st.markdown("---")

        # Funding charts
        for symbol, data in all_data.items():
            ticker = data["ticker"]
            dm = data["deriv_metrics"]
            funding_df = data["funding_df"]

            st.markdown(f"### {ticker} Funding Analysis")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("#### Funding Rate Chart")
                st.caption(
                    "This chart displays the **annualized funding rate** for perpetual futures contracts over time. "
                    "**Green bars above the 0% line** indicate positive funding rates (longs pay shorts), suggesting bullish market sentiment "
                    "and potential long positioning dominance. **Red bars below the 0% line** indicate negative funding rates (shorts pay longs), "
                    "suggesting bearish sentiment and potential short positioning dominance. The funding rate is a mechanism that keeps perpetual "
                    "futures prices aligned with the spot price. High positive funding rates (>50% annualized) may indicate crowded longs and "
                    "correction risk, while extreme negative rates (<-50%) may signal crowded shorts and squeeze potential. "
                    "The grey horizontal line at 0% represents the neutral point where no funding payments occur."
                )
                st.plotly_chart(create_funding_chart(funding_df, ticker), use_container_width=True, key=f"funding_{ticker}")

            with col2:
                # Sentiment card
                if dm.latest_funding_annualized is not None:
                    if dm.latest_funding_annualized > 0.1:
                        st.success(f"🐂 **BULLISH**\n\n{dm.funding_comment}")
                    elif dm.latest_funding_annualized < -0.1:
                        st.error(f"🐻 **BEARISH**\n\n{dm.funding_comment}")
                    else:
                        st.info(f"⚖️ **NEUTRAL**\n\n{dm.funding_comment}")
                
                # Stats
                st.markdown("**Funding Stats (7d)**")
                st.caption(f"Mean: {dm.mean_funding_annualized:.1%}" if dm.mean_funding_annualized else "Mean: N/A")
                st.caption(f"Max: {dm.max_funding_annualized:.1%}" if dm.max_funding_annualized else "Max: N/A")
                st.caption(f"Min: {dm.min_funding_annualized:.1%}" if dm.min_funding_annualized else "Min: N/A")

            st.markdown("---")

    # =============================================================================
    # TAB 4: OPTIONS ANALYTICS
    # =============================================================================
    with tab_options:
        st.markdown("### 📉 Options Analytics")
        st.caption("Max Pain, Implied Volatility, and Skew analysis")

        for symbol, data in all_data.items():
            ticker = data["ticker"]
            opts = data["options_data"]
            tech = data["technicals"]

            if not opts:
                st.info(f"📊 No options data available for {ticker}")
                continue

            st.markdown(f"### {ticker} Options ({opts['expiry']})")

            # Simplified metrics row - only Spot Price and Max Pain
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("💵 Spot Price", format_currency(opts["spot"]))
            with col2:
                st.metric("🎯 Max Pain", format_currency(opts["max_pain"]))
            with col3:
                skew = opts["skew_25d"]
                skew_label = "🔴 Put Heavy" if skew > 0.02 else ("🟢 Call Heavy" if skew < -0.02 else "⚪ Balanced")
                st.metric("📊 25Δ Skew", f"{skew:.1%}")
                st.caption(skew_label)

            st.markdown("---")

            # Charts row 1: Skew Pie
            st.markdown("#### Put/Call IV Positioning")
            st.plotly_chart(create_skew_pie(opts.get("put_iv", 0), opts.get("call_iv", 0), ticker), use_container_width=True, key=f"skew_pie_{ticker}")

            # IV Smile chart
            st.plotly_chart(create_iv_smile_chart(opts, ticker), use_container_width=True, key=f"iv_smile_{ticker}")

            st.markdown("---")

        # Interpretation guides
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("📖 Max Pain Guide", expanded=False):
                st.markdown(
                    """
                    **Max Pain** is the strike price where option buyers lose the most money.
                    
                    - Price tends to gravitate toward max pain near expiration
                    - Large distance from spot suggests potential price movement
                    - Use as support/resistance level
                    """
                )

        with col2:
            with st.expander("📊 IV Skew Guide", expanded=False):
                st.markdown(
                    """
                    **Put/Call IV Skew:**
                    - **Put Heavy (Fear)** → Downside protection demand
                    - **Call Heavy (Greed)** → Upside speculation
                    - **Balanced** → Neutral sentiment
                    """
                )

    # =============================================================================
    # TAB 5: ETF FLOW ANALYSIS
    # =============================================================================
    with tab_etf:
        st.markdown("### 📊 ETF Flow & Demand Dashboard")
        st.caption("Analysis of **FNGS, XLG, QQQ, and MGK** to understand institutional demand drivers.")

        etf_tickers = ['FNGS', 'XLG', 'QQQ', 'MGK']
        issuer_map = {
            'FNGS': 'MicroSectors (BMO)',
            'XLG': 'Invesco (Top 50)',
            'QQQ': 'Invesco (Nasdaq)',
            'MGK': 'Vanguard (Mega Cap)'
        }

        @st.cache_data
        def fetch_etf_data(tickers, period="1y"):
            """Fetches ETF data from yfinance and calculates flow metrics."""
            data = yf.download(tickers, period=period, group_by='ticker', auto_adjust=True)
            processed_data = {}
            summary_list = []

            for ticker in tickers:
                try:
                    df = data[ticker].copy()
                    if df.empty:
                        continue
                except KeyError:
                    continue

                # Calculate Flow Proxy
                df['Price_Change'] = df['Close'].diff()
                df['Direction'] = np.sign(df['Price_Change'])
                df['Direction'] = df['Direction'].replace(0, method='ffill')
                df['Daily_Flow_Est'] = df['Close'] * df['Volume'] * df['Direction']

                # Calculate Weekly Flow
                weekly_flow = df['Daily_Flow_Est'].resample('W').sum()
                current_weekly_flow = weekly_flow.iloc[-1] if not weekly_flow.empty else 0

                # Calculate Flow Streak
                df['Flow_Sign'] = np.sign(df['Daily_Flow_Est'])
                df['Flow_Sign'] = df['Flow_Sign'].replace(0, method='ffill').replace(0, method='bfill')
                df['Flow_Sign'] = df['Flow_Sign'].replace(0, 1)
                
                if not df.empty and len(df) > 0:
                    streak_values = []
                    current_sign = None
                    current_streak = 0
                    
                    for sign in df['Flow_Sign'].values:
                        if pd.isna(sign):
                            streak_values.append(0)
                            current_streak = 0
                            current_sign = None
                            continue
                        
                        sign = int(sign)
                        
                        if current_sign is None or sign != current_sign:
                            current_sign = sign
                            current_streak = 1
                        else:
                            current_streak += 1
                        
                        streak_values.append(int(current_streak * sign))
                    
                    df['Streak'] = streak_values
                    streak_val = int(df['Streak'].iloc[-1]) if not df.empty and len(df['Streak']) > 0 else 0
                else:
                    df['Streak'] = 0
                    streak_val = 0

                # Calculate Acceleration
                df['Flow_MA20'] = df['Daily_Flow_Est'].rolling(window=20).mean()
                if not df.empty and not pd.isna(df['Flow_MA20'].iloc[-1]):
                    acceleration = df['Daily_Flow_Est'].iloc[-1] - df['Flow_MA20'].iloc[-1]
                    acc_status = "SPEEDING UP" if acceleration > 0 else "SLOWING DOWN"
                else:
                    acc_status = "N/A"

                df['Norm_Price'] = (df['Close'] / df['Close'].iloc[0]) * 100

                processed_data[ticker] = df

                summary_list.append({
                    'Ticker': ticker,
                    'Issuer': issuer_map.get(ticker, 'Unknown'),
                    'Price': df['Close'].iloc[-1] if not df.empty else 0,
                    'Daily Net Flow ($M)': round(df['Daily_Flow_Est'].iloc[-1] / 1_000_000, 2) if not df.empty else 0,
                    'Weekly Net Flow ($M)': round(current_weekly_flow / 1_000_000, 2),
                    'Streak (Days)': int(streak_val),
                    'Acceleration': acc_status,
                    'Total_Flow_Abs': df['Daily_Flow_Est'].abs().sum() if not df.empty else 0
                })
            
            summary_df = pd.DataFrame(summary_list)
            return processed_data, summary_df

        # Fetch ETF data (etf_period is set in main sidebar)
        with st.spinner('Fetching ETF data...'):
            etf_processed_data, etf_summary_df = fetch_etf_data(etf_tickers, etf_period)

        # Summary Metrics
        st.markdown("#### 📝 Summary Metrics")
        if not etf_summary_df.empty:
            dominant_issuer = etf_summary_df.sort_values(by='Total_Flow_Abs', ascending=False).iloc[0]
            st.markdown(f"🏆 **Dominant Issuer (Total Flow Volume):** {dominant_issuer['Issuer']} ({dominant_issuer['Ticker']})")
            st.dataframe(etf_summary_df.drop(columns=['Total_Flow_Abs']).style.format({"Price": "${:.2f}"}), use_container_width=True)

        st.markdown("---")

        # Detailed 20-Day Table
        st.markdown("#### 📊 Detailed 20-Day Flow Analysis")
        st.markdown("""
        **Streak Definition:** Counts consecutive days with money flow in the same direction (Buy or Sell).
        - **Positive numbers (e.g., +5, +10):** Consecutive days of buying (institutional accumulation)
        - **Negative numbers (e.g., -3, -7):** Consecutive days of selling (institutional distribution)
        - **Small numbers (e.g., +1, -1, +2):** Market is sideways, no clear trend
        """)

        for ticker in etf_tickers:
            if ticker not in etf_processed_data:
                continue
            
            df = etf_processed_data[ticker]
            if df.empty:
                continue
            
            with st.expander(f"📈 {ticker} - Last 20 Days", expanded=False):
                df_last_20 = df.tail(20).copy()
                
                detail_table = pd.DataFrame({
                    'Date': df_last_20.index.strftime('%Y-%m-%d'),
                    'Price': df_last_20['Close'].round(2),
                    'Volume': df_last_20['Volume'].apply(lambda x: f"{x:,.0f}"),
                    'Daily Flow ($M)': (df_last_20['Daily_Flow_Est'] / 1_000_000).round(2),
                    'Streak (Days)': df_last_20['Streak'].astype(int),
                })
                
                styled_table = detail_table.style.format({
                    'Price': '${:.2f}',
                    'Daily Flow ($M)': '${:.2f}M',
                })
                
                st.dataframe(styled_table, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Performance & Flow Plots
        st.markdown("#### 📈 Performance & Flow Analysis")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Relative Performance (Rebased to 100)**")
            fig_perf = go.Figure()
            for ticker in etf_tickers:
                if ticker in etf_processed_data:
                    df = etf_processed_data[ticker]
                    fig_perf.add_trace(go.Scatter(x=df.index, y=df['Norm_Price'], mode='lines', name=ticker))
            fig_perf.update_layout(yaxis_title="Growth (%)", hovermode="x unified", template="plotly_white")
            st.plotly_chart(fig_perf, use_container_width=True)

        with col2:
            st.markdown("**Estimated Institutional Money Flow (Daily)**")
            fig_flow = go.Figure()
            for ticker in etf_tickers:
                if ticker in etf_processed_data:
                    df = etf_processed_data[ticker]
                    fig_flow.add_trace(go.Scatter(x=df.index, y=df['Daily_Flow_Est'] / 1_000_000, mode='lines', name=ticker))
            fig_flow.add_hline(y=0, line_dash="dash", line_color="black")
            fig_flow.update_layout(yaxis_title="Estimated Flow ($ Millions)", hovermode="x unified", template="plotly_white")
            st.plotly_chart(fig_flow, use_container_width=True)

    # =============================================================================
    # TAB 6: POLYMARKET PREDICTIONS
    # =============================================================================
    with tab_polymarket:
        st.markdown("### 🎯 Polymarket Predictions")
        st.caption("Market predictions and probability analysis from Polymarket (Future Events Only)")
        
        # Extract unique tickers from selected symbols
        unique_tickers = list(set([extract_ticker(s) for s in selected_symbols]))
        unique_tickers.sort()
        
        if not unique_tickers:
            st.info("Please select symbols in the sidebar to view Polymarket predictions.")
            st.markdown("---")
            return

        # Helper functions from polymarket_price_predictions.py
        def safe_json_list(value):
            """Safely parse JSON list from various formats."""
            if value is None:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                s = value.strip()
                if not s:
                    return []
                try:
                    return json.loads(s)
                except Exception:
                    try:
                        return json.loads(s.replace("'", '"'))
                    except Exception:
                        return []
            return []

        def extract_yes_probability(market):
            """Extract YES probability from market data."""
            outcomes = safe_json_list(market.get("outcomes"))
            prices = safe_json_list(market.get("outcomePrices"))
            
            fprices = []
            for p in prices:
                try:
                    fprices.append(float(p))
                except Exception:
                    fprices.append(float("nan"))
            
            if outcomes and fprices and len(outcomes) == len(fprices):
                for i, o in enumerate(outcomes):
                    if isinstance(o, str) and o.strip().lower() == "yes":
                        return fprices[i] if pd.notna(fprices[i]) else None
            
            if fprices:
                return fprices[0] if pd.notna(fprices[0]) else None
            return None

        def market_target_label(market):
            """Get market target label."""
            return (
                market.get("groupItemTitle")
                or market.get("question")
                or market.get("slug")
                or "Unknown"
            )

        def sort_key_from_label(label):
            """Create sort key from label."""
            nums = re.findall(r"\d+(?:\.\d+)?", label.replace(",", ""))
            key = float(nums[0]) if nums else 0.0
            if "<" in label:
                key -= 0.1
            elif ">" in label:
                key += 0.1
            return key

        @st.cache_data(ttl=3600)
        def search_polymarket_events(query, max_pages=3):
            """Search for Polymarket events."""
            base_url = "https://gamma-api.polymarket.com"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            
            seen = {}
            for page in range(1, max_pages + 1):
                try:
                    url = f"{base_url}/public-search"
                    params = {
                        "q": query,
                        "page": page,
                        "limit_per_type": 50,
                        "keep_closed_markets": 1,
                        "events_status": "all",
                    }
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    response.raise_for_status()
                    payload = response.json()
                    
                    events = payload.get("events") or []
                    for ev in events:
                        slug = ev.get("slug")
                        if slug:
                            seen[slug] = ev
                    
                    pagination = payload.get("pagination") or {}
                    if not pagination.get("hasMore"):
                        break
                    
                    time.sleep(0.15)
                except Exception as e:
                    break
            
            return list(seen.values())

        @st.cache_data(ttl=3600)
        def get_event_by_slug(slug):
            """Get full event data by slug."""
            base_url = "https://gamma-api.polymarket.com"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            try:
                url = f"{base_url}/events/slug/{slug}"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception:
                return None

        # Search for predictions for all selected tickers
        today = datetime.now(timezone.utc)
        all_future_events = {}  # {ticker: [events]}
        
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        total_tickers = len(unique_tickers)
        for idx, ticker in enumerate(unique_tickers):
            progress = (idx + 1) / total_tickers
            progress_bar.progress(progress)
            progress_text.text(f"🔍 Searching {ticker}... ({idx + 1}/{total_tickers})")
            
            # Build search queries for this ticker
            queries = [
                f"{ticker} {polymarket_year}",
                f"{ticker} close {polymarket_year}",
                f"{ticker} closes {polymarket_year}",
                f"{ticker} hit {polymarket_year}",
            ]
            
            # Search for events
            all_events = []
            for query in queries:
                events = search_polymarket_events(query, max_pages=2)
                all_events.extend(events)
            
            # Dedupe by slug
            seen_slugs = set()
            unique_events = []
            for ev in all_events:
                slug = ev.get("slug")
                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    unique_events.append(ev)
            
            # Filter events where endDate > today
            future_events = []
            for ev_stub in unique_events:
                end_date_str = ev_stub.get("endDate")
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        if end_date > today:
                            # Fetch full event data
                            slug = ev_stub.get("slug")
                            if slug:
                                full_event = get_event_by_slug(slug)
                                if full_event:
                                    future_events.append(full_event)
                    except Exception:
                        continue
            
            if future_events:
                all_future_events[ticker] = future_events
            
            time.sleep(0.2)  # Small delay to avoid rate limiting
        
        progress_bar.empty()
        progress_text.empty()
        
        # Display results
        total_events = sum(len(events) for events in all_future_events.values())
        if total_events == 0:
            st.info(f"No future events found for {', '.join(unique_tickers)} in {polymarket_year}. Try a different year.")
        else:
            st.success(f"Found {total_events} future event(s) across {len(all_future_events)} ticker(s)")
            st.markdown("---")
            
            # Display bar plots grouped by ticker
            for ticker in unique_tickers:
                if ticker not in all_future_events:
                    continue
                
                events = all_future_events[ticker]
                st.markdown(f"### 📊 {ticker} Predictions")
                
                for event in events:
                    markets = event.get('markets', [])
                    if not markets:
                        continue
                    
                    rows = []
                    for market in markets:
                        label = market_target_label(market)
                        yes_p = extract_yes_probability(market)
                        
                        if yes_p is not None:
                            rows.append({
                                "Target": label,
                                "Probability": yes_p,
                                "SortKey": sort_key_from_label(label)
                            })
                    
                    if rows:
                        df = pd.DataFrame(rows)
                        df = df.sort_values(by="SortKey")
                        
                        # Create bar plot
                        event_title = event.get('title', 'Unknown Event')
                        event_end = event.get('endDate', '')
                        
                        with st.expander(f"📈 {event_title}", expanded=True):
                            if event_end:
                                try:
                                    end_date = datetime.fromisoformat(event_end.replace("Z", "+00:00"))
                                    st.caption(f"End Date: {end_date.strftime('%Y-%m-%d %H:%M UTC')}")
                                except Exception:
                                    st.caption(f"End Date: {event_end}")
                            
                            fig = go.Figure()
                            
                            colors = ['#10b981' if p > 0.2 else '#f43f5e' if p < 0.05 else '#6366f1' for p in df['Probability']]
                            
                            fig.add_trace(go.Bar(
                                x=df['Target'],
                                y=df['Probability'],
                                marker_color=colors,
                                text=[f"{p:.1%}" for p in df['Probability']],
                                textposition='outside',
                                name='Probability'
                            ))
                            
                            fig.update_layout(
                                title=f"{ticker} Price Prediction",
                                xaxis_title="Price Target (USD)",
                                yaxis_title="Probability",
                                yaxis_tickformat='.0%',
                                template="plotly_white",
                                hovermode="x unified",
                                height=500
                            )
                            fig.update_xaxes(tickangle=45)
                            
                            st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #71717a; padding: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
            Data from Hyperliquid & Yahoo Finance
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

