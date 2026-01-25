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
    create_macro_event_chart,
    create_macro_panel_chart,
    create_price_chart,
    create_rsi_chart,
    create_skew_pie,
    create_treasury_spread_chart,
    create_treasury_yields_chart,
    create_volume_chart,
)
from src.config import SYMBOLS
from src.data_classes import DerivativesMetrics
from src.derivatives import compute_derivatives_metrics
from src.llm_predictions import (
    build_event_payload,
    has_openai_key,
    has_gemini_key,
    llm_filter_predictions,
    DEFAULT_MODEL,
    DEFAULT_GEMINI_MODEL,
    COMPANY_ALIASES,
)
from src.options import fetch_options_data, clear_options_cache
from src.technicals import compute_all_technicals
from src.utils import extract_ticker, format_currency, format_pct
from macro_panel import fetch_prices_strict, FetchConfig, PANEL, DISPLAY_ORDER, compute_snapshot
from treasury_yields import fetch_treasury_yields, SERIES


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
            st.caption("⏱️ 5 min")
        with col2:
            st.markdown("**Price**")
            st.caption("⏱️ 4 hours")
        
        # Cache clearing button
        if st.button("🔄 Clear Options Cache"):
            clear_options_cache()
            st.success("✅ Options cache cleared!")
            st.rerun()

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
    tab_overview, tab_technicals, tab_derivatives, tab_options, tab_etf, tab_polymarket, tab_macro, tab_treasury = st.tabs(
        ["📈 Market Snapshot", "📊 Technical Analysis", "🔥 Derivatives Intel", "📉 Options Analytics", "📊 ETF Flow", "🎯 Polymarket Predictions", "🌍 Market Index & Macro Event", "📊 Treasury Yields"]
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
                st.metric("📊 Volume", f"{tech.get('volume_24h', 0):,.0f} Tokens")
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
    # TAB 5: ETF Flow
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

        # Fetch ETF data
        with st.spinner('Fetching ETF data...'):
            etf_processed_data, etf_summary_df = fetch_etf_data(etf_tickers, "1y")

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
            st.markdown("**Relative Performance**")
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
        
        # Default year for Polymarket predictions
        polymarket_year = 2026
        
        # Extract unique tickers from selected symbols
        unique_tickers = list(set([extract_ticker(s) for s in selected_symbols]))
        unique_tickers.sort()
        
        if not unique_tickers:
            st.info("Please select symbols in the sidebar to view Polymarket predictions.")
            st.markdown("---")
            return

        llm_enabled = st.checkbox(
            "🤖 Use LLM to filter related predictions",
            value=has_openai_key(),
            help="Requires OPENAI_API_KEY in your environment.",
        )
        llm_provider = st.selectbox(
            "LLM provider",
            options=["openai", "gemini"],
            index=0,
        )
        llm_model_default = DEFAULT_MODEL if llm_provider == "openai" else DEFAULT_GEMINI_MODEL
        llm_model = st.text_input(
            "LLM model",
            value=llm_model_default,
            help="Overrides default model for the selected provider.",
        )
        if llm_enabled and not has_openai_key():
            st.info("Set `OPENAI_API_KEY` to enable LLM filtering.")
        if llm_enabled and llm_provider == "gemini" and not has_gemini_key():
            st.info("Set `GEMINI_API_KEY` to enable Gemini filtering.")

        include_non_price = st.checkbox(
            "Include non-price prediction queries (earnings, guidance, M&A)",
            value=True,
            help="Adds more search queries beyond price targets.",
        )

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

        def is_stock_prediction_event(event):
            """Filter to price, volume, revenue, or stock outlook/insight events."""
            allowed_keywords = [
                "price",
                "target",
                "close",
                "closes",
                "hit",
                "above",
                "below",
                "volume",
                "revenue",
                "sales",
                "outlook",
                "guidance",
                "forecast",
                "insight",
                "stock",
                "shares",
            ]
            text_parts = [
                event.get("title", ""),
                event.get("slug", ""),
                event.get("description", ""),
            ]
            for market in event.get("markets", []) or []:
                text_parts.append(market.get("question", ""))
                text_parts.append(market.get("groupItemTitle", ""))
                text_parts.append(market.get("slug", ""))
            haystack = " ".join([p for p in text_parts if p]).lower()
            return any(k in haystack for k in allowed_keywords)

        def is_volume_event(event):
            """Identify volume-focused prediction events."""
            volume_keywords = [
                "volume",
                "trading volume",
                "shares traded",
                "turnover",
                "liquidity",
            ]
            text_parts = [
                event.get("title", ""),
                event.get("slug", ""),
                event.get("description", ""),
            ]
            for market in event.get("markets", []) or []:
                text_parts.append(market.get("question", ""))
                text_parts.append(market.get("groupItemTitle", ""))
                text_parts.append(market.get("slug", ""))
            haystack = " ".join([p for p in text_parts if p]).lower()
            return any(k in haystack for k in volume_keywords)

        def compute_polymarket_perp_signal(events):
            """Infer a long/short bias from Polymarket markets."""
            long_keywords = ["long", "bullish", "up", "rise", "higher", "above", "increase"]
            short_keywords = ["short", "bearish", "down", "fall", "lower", "below", "decrease"]
            long_probs = []
            short_probs = []
            used_markets = []
            for ev in events:
                for market in ev.get("markets", []) or []:
                    question = " ".join([
                        market.get("question", ""),
                        market.get("groupItemTitle", ""),
                        market.get("slug", ""),
                    ]).lower()
                    yes_p = extract_yes_probability(market)
                    if yes_p is None:
                        continue
                    if any(k in question for k in long_keywords):
                        long_probs.append(yes_p)
                        used_markets.append({
                            "Event": ev.get("title", "Unknown Event"),
                            "Market": market.get("question") or market.get("groupItemTitle") or market.get("slug") or "Unknown",
                            "Direction": "Long/Bullish",
                            "YesProbability": yes_p,
                        })
                    if any(k in question for k in short_keywords):
                        short_probs.append(yes_p)
                        used_markets.append({
                            "Event": ev.get("title", "Unknown Event"),
                            "Market": market.get("question") or market.get("groupItemTitle") or market.get("slug") or "Unknown",
                            "Direction": "Short/Bearish",
                            "YesProbability": yes_p,
                        })

            long_avg = float(np.mean(long_probs)) if long_probs else None
            short_avg = float(np.mean(short_probs)) if short_probs else None

            if long_avg is None and short_avg is None:
                return {"signal": "No signal", "long_avg": None, "short_avg": None, "count": 0, "markets": []}
            if short_avg is None:
                return {
                    "signal": "Long bias",
                    "long_avg": long_avg,
                    "short_avg": None,
                    "count": len(long_probs),
                    "markets": used_markets,
                }
            if long_avg is None:
                return {
                    "signal": "Short bias",
                    "long_avg": None,
                    "short_avg": short_avg,
                    "count": len(short_probs),
                    "markets": used_markets,
                }

            diff = long_avg - short_avg
            if diff > 0.1:
                signal = "Long bias"
            elif diff < -0.1:
                signal = "Short bias"
            else:
                signal = "Neutral"

            return {
                "signal": signal,
                "long_avg": long_avg,
                "short_avg": short_avg,
                "count": len(long_probs) + len(short_probs),
                "markets": used_markets,
            }

        @st.cache_data(ttl=900, show_spinner=False)
        def llm_filter_predictions_cached(symbol, events_payload, model_name, provider_name):
            return llm_filter_predictions(
                symbol,
                events_payload,
                model=model_name,
                provider=provider_name,
            )

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
            base_queries = [
                f"{ticker} {polymarket_year}",
                f"{ticker} close {polymarket_year}",
                f"{ticker} closes {polymarket_year}",
                f"{ticker} price {polymarket_year}",
                f"{ticker} hit {polymarket_year}",
            ]
            aliases = COMPANY_ALIASES.get(ticker, [])
            for alias in aliases:
                base_queries.append(f"{alias} {polymarket_year}")
                base_queries.append(f"{alias} stock {polymarket_year}")

            extra_queries = []
            if include_non_price:
                extra_queries = [
                    f"{ticker} earnings {polymarket_year}",
                    f"{ticker} EPS {polymarket_year}",
                    f"{ticker} revenue {polymarket_year}",
                    f"{ticker} trading volume {polymarket_year}",
                    f"{ticker} volume {polymarket_year}",
                    f"{ticker} shares traded {polymarket_year}",
                    f"{ticker} turnover {polymarket_year}",
                    f"{ticker} bullish {polymarket_year}",
                    f"{ticker} bearish {polymarket_year}",
                    f"{ticker} long {polymarket_year}",
                    f"{ticker} short {polymarket_year}",
                    f"{ticker} guidance {polymarket_year}",
                    f"{ticker} acquisition",
                    f"{ticker} merger",
                    f"{ticker} bankruptcy",
                    f"{ticker} dividend",
                    f"{ticker} buyback",
                    f"{ticker} CEO",
                ]
                for alias in aliases:
                    extra_queries.append(f"{alias} earnings {polymarket_year}")
                    extra_queries.append(f"{alias} EPS {polymarket_year}")
                    extra_queries.append(f"{alias} guidance {polymarket_year}")
                    extra_queries.append(f"{alias} volume {polymarket_year}")
                    extra_queries.append(f"{alias} trading volume {polymarket_year}")

            queries = list(dict.fromkeys(base_queries + extra_queries))
            
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
                                    # Filter out unwanted events
                                    event_title = full_event.get('title', '').lower()
                                    event_slug = full_event.get('slug', '').lower()
                                    
                                    # Skip if title or slug contains "hit" pattern (cumulative markets)
                                    if 'hit' in event_title or 'hit' in event_slug:
                                        continue
                                    
                                    # Skip non-stock related events (e.g., Sanremo, music festivals, etc.)
                                    unwanted_keywords = ['sanremo', 'winner', 'festival', 'music', 'election', 'sport']
                                    if any(keyword in event_title or keyword in event_slug for keyword in unwanted_keywords):
                                        continue

                                    if not is_stock_prediction_event(full_event):
                                        continue
                                    
                                    future_events.append(full_event)
                    except Exception:
                        continue
            
            if future_events:
                all_future_events[ticker] = future_events
            
            time.sleep(0.2)  # Small delay to avoid rate limiting
        
        progress_bar.empty()
        progress_text.empty()

        llm_results = {}
        if llm_enabled and all_future_events:
            llm_progress_text = st.empty()
            llm_progress_bar = st.progress(0)
            llm_total = len(all_future_events)
            for idx, (ticker, events) in enumerate(all_future_events.items()):
                llm_progress = (idx + 1) / llm_total
                llm_progress_bar.progress(llm_progress)
                llm_progress_text.text(f"🤖 LLM filtering {ticker}... ({idx + 1}/{llm_total})")
                try:
                    payload = build_event_payload(events)
                    llm_results[ticker] = llm_filter_predictions_cached(ticker, payload, llm_model, llm_provider)
                except Exception as e:
                    llm_results[ticker] = {"related_events": [], "summary": "", "error": str(e)}
            llm_progress_bar.empty()
            llm_progress_text.empty()
        
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
                base_event_count = len(events)
                llm_result = llm_results.get(ticker)
                if llm_enabled and llm_result and not llm_result.get("error"):
                    related = llm_result.get("related_events") or []
                    related_slugs = {r.get("slug") for r in related if r.get("slug")}
                    if related_slugs:
                        events = [ev for ev in events if ev.get("slug") in related_slugs]
                        st.caption(f"🤖 LLM matched {len(events)} of {base_event_count} event(s).")
                    else:
                        st.caption("🤖 LLM found no related events for this symbol.")
                    summary = llm_result.get("summary")
                    if summary:
                        st.info(f"🤖 {summary}")
                elif llm_enabled and llm_result and llm_result.get("error"):
                    st.warning(f"LLM filtering error for {ticker}: {llm_result.get('error')}")

                if not events:
                    st.info("No related prediction events to display.")
                    st.markdown("---")
                    continue

                perp_signal = compute_polymarket_perp_signal(events)
                st.markdown("#### 📍 Perp Long/Short Signal (Polymarket)")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Signal", perp_signal["signal"])
                with col2:
                    long_avg = perp_signal.get("long_avg")
                    st.metric("Long prob (avg)", f"{long_avg:.1%}" if long_avg is not None else "N/A")
                with col3:
                    short_avg = perp_signal.get("short_avg")
                    st.metric("Short prob (avg)", f"{short_avg:.1%}" if short_avg is not None else "N/A")
                if perp_signal.get("count", 0) > 0:
                    st.caption(f"Based on {perp_signal['count']} market(s).")
                    markets_df = pd.DataFrame(perp_signal.get("markets", []))
                    if not markets_df.empty:
                        st.dataframe(
                            markets_df,
                            use_container_width=True,
                            hide_index=True,
                        )
                st.markdown("---")

                volume_events = [ev for ev in events if is_volume_event(ev)]
                non_volume_events = [ev for ev in events if ev not in volume_events]
                if volume_events:
                    st.markdown("#### 📊 Volume Predictions")
                event_groups = [(volume_events, True), (non_volume_events, False)]
                
                for group_events, is_volume in event_groups:
                    for event in group_events:
                        markets = event.get('markets', [])
                        if not markets:
                            continue
                        rows = []
                        seen_labels = {}  # Track best probability for each label
                        for market in markets:
                            label = market_target_label(market)
                            yes_p = extract_yes_probability(market)
                            
                            if yes_p is not None:
                                # For range markets, if same label appears multiple times,
                                # keep the one with highest probability (or non-zero if available)
                                if label in seen_labels:
                                    # Only update if this probability is more meaningful
                                    current_prob = seen_labels[label]
                                    if yes_p > current_prob or (current_prob == 0 and yes_p > 0):
                                        seen_labels[label] = yes_p
                                else:
                                    seen_labels[label] = yes_p
                        
                        # Convert to list of rows
                        for label, prob in seen_labels.items():
                            rows.append({
                                "Target": label,
                                "Probability": prob,
                                "SortKey": sort_key_from_label(label)
                            })
                        
                        if len(rows) <= 1:
                            continue
                        if rows:
                            df = pd.DataFrame(rows)
                            df = df.sort_values(by="SortKey")
                            if df["Probability"].fillna(0).max() <= 0:
                                continue
                            
                            # For cumulative markets (like "Will it hit $X?"), multiple values can be 100%
                            # This is normal - it means the price has already exceeded those levels
                            
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
                                
                                # Add explanation for cumulative markets
                                total_prob = df['Probability'].sum()
                                max_prob_count = (df['Probability'] >= 0.99).sum()
                                if max_prob_count > 1 and total_prob > 2:
                                    st.info(
                                        "ℹ️ **Note:** This is a cumulative market. Multiple price targets can have high probabilities because each "
                                        "market asks 'Will the price hit $X?' independently. If the current price exceeds a target, that target "
                                        "shows ~100%. **Example:** Current price $180 → 'Hit $150?' ≈100%, 'Hit $170?' ≈100%, 'Hit $200?' might be 40%."
                                    )
                                
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
                                    xaxis_title="Prediction Target",
                                    yaxis_title="Probability",
                                    yaxis_tickformat='.0%',
                                    template="plotly_white",
                                    hovermode="x unified",
                                    height=500
                                )
                                fig.update_xaxes(tickangle=45)
                                
                                group_prefix = "vol" if is_volume else "other"
                                plot_key = f"pm_{group_prefix}_{ticker}_{event.get('slug', event_title)}"
                                st.plotly_chart(fig, use_container_width=True, key=plot_key)
                
                st.markdown("---")

    # =============================================================================
    # TAB 7: Market Index & Macro Event
    # =============================================================================
    with tab_macro:
        st.markdown("### 🌍 Market Index & Macro Event Dashboard")
        st.caption("Real-time macro indicators: DXY (Dollar Index), VIX (Volatility), S&P 500, Gold, and Oil")
        
        # Fetch macro data
        @st.cache_data(ttl=3600)  # Cache for 1 hour
        def fetch_macro_data(period: str, interval: str):
            """Fetch Market Index & Macro Event data."""
            cfg = FetchConfig(period=period, interval=interval, auto_adjust=False)
            try:
                prices = fetch_prices_strict(PANEL, cfg)
                snapshot = compute_snapshot(prices)
                return prices, snapshot
            except Exception as e:
                st.error(f"Error fetching macro data: {str(e)}")
                return pd.DataFrame(), pd.DataFrame()
        
        with st.spinner('🔄 Fetching macro data...'):
            # Use default values: 6mo period, 1d interval
            macro_prices, macro_snapshot = fetch_macro_data("6mo", "1d")
        
        if macro_prices.empty:
            st.warning("⚠️ Unable to fetch macro data. Please try again later.")
        else:
            # Summary metrics
            st.markdown("#### 📊 Current Values & Returns")
            
            if not macro_snapshot.empty:
                # Create metrics columns
                cols = st.columns(len(macro_snapshot))
                for idx, (symbol, row) in enumerate(macro_snapshot.iterrows()):
                    with cols[idx]:
                        last_val = row["Last"]
                        ret_1 = row["Ret_1"]
                        ret_5 = row["Ret_5"]
                        ret_21 = row["Ret_21"]
                        
                        # Format value based on symbol
                        if symbol == "VIX":
                            val_str = f"{last_val:.2f}"
                        elif symbol == "DXY":
                            val_str = f"{last_val:.2f}"
                        elif symbol == "S&P 500":
                            val_str = f"{last_val:,.0f}"
                        elif symbol == "Gold":
                            val_str = f"${last_val:,.0f}"
                        elif symbol == "Oil":
                            val_str = f"${last_val:.2f}"
                        else:
                            val_str = f"{last_val:.2f}"
                        
                        # Color indicators
                        trend_1d = "🟢" if ret_1 > 0 else ("🔴" if ret_1 < 0 else "⚪")
                        trend_5d = "🟢" if ret_5 > 0 else ("🔴" if ret_5 < 0 else "⚪")
                        trend_21d = "🟢" if ret_21 > 0 else ("🔴" if ret_21 < 0 else "⚪")
                        
                        st.markdown(f"#### {symbol}")
                        st.metric("Current", val_str)
                        st.metric(
                            f"{trend_1d} 1d",
                            f"{ret_1:+.2f}%",
                            delta_color="normal" if ret_1 >= 0 else "inverse",
                        )
                        st.metric(
                            f"{trend_5d} 5d",
                            f"{ret_5:+.2f}%",
                            delta_color="normal" if ret_5 >= 0 else "inverse",
                        )
                        st.metric(
                            f"{trend_21d} 21d",
                            f"{ret_21:+.2f}%",
                            delta_color="normal" if ret_21 >= 0 else "inverse",
                        )
            
            st.markdown("---")
            
            # Main chart
            st.markdown("#### 📈 Market Index Chart")
            st.caption(
                "Interactive chart showing the evolution of key macro indicators over time. "
                "Hover over the chart to see detailed values and percentage changes. "
                "Green fill indicates positive momentum, red fill indicates negative momentum."
            )
            
            macro_chart = create_macro_panel_chart(macro_prices)
            st.plotly_chart(macro_chart, use_container_width=True)
            
            st.markdown("---")
            
            # Detailed snapshot table
            st.markdown("#### 📋 Detailed Snapshot")
            if not macro_snapshot.empty:
                display_snapshot = macro_snapshot.copy()
                display_snapshot.columns = ["Last Value", "1-Day Return (%)", "5-Day Return (%)", "21-Day Return (%)"]
                st.dataframe(
                    display_snapshot.style.format({
                        "Last Value": "{:,.2f}",
                        "1-Day Return (%)": "{:+.2f}",
                        "5-Day Return (%)": "{:+.2f}",
                        "21-Day Return (%)": "{:+.2f}",
                    }),
                    use_container_width=True,
                )
            
            # Info expander
            with st.expander("📖 Macro Indicators Guide", expanded=False):
                st.markdown(
                    """
                    | Indicator | Description | What It Measures |
                    |-----------|-------------|------------------|
                    | **DXY** | US Dollar Index | Strength of USD against basket of currencies |
                    | **VIX** | CBOE Volatility Index | Market fear/volatility expectations (30-day) |
                    | **S&P 500** | S&P 500 Index | Performance of 500 largest US companies |
                    | **Gold** | Gold Futures (GC=F) | Precious metal commodity price |
                    | **Oil** | Crude Oil Futures (CL=F) | Energy commodity price (WTI) |
                    
                    **Interpretation:**
                    - **DXY ↑**: Strong dollar → often negative for commodities/emerging markets
                    - **VIX ↑**: High fear → potential market stress/correction risk
                    - **S&P 500 ↑**: Bullish equity sentiment
                    - **Gold ↑**: Safe haven demand, inflation hedge
                    - **Oil ↑**: Economic growth expectations, supply/demand dynamics
                    """
                )
            
            st.markdown("---")
            
            # =====================================================================
            # INFLATION & FED RATE INDICATORS
            # =====================================================================
            st.markdown("### 📊 Inflation & Federal Reserve Indicators")
            st.caption("CPI, PCE, PPI inflation rates and Federal Funds Rate from FRED (Federal Reserve Economic Data)")
            
            # FRED API key and series definitions
            FRED_API_KEY = '3e6b3d277d0889cb78aebd2cd1548181'
            MACRO_EVENT_SERIES = {
                'CPI (Consumer Inflation)': 'CPIAUCSL',
                'PCE (Fed Target Inflation)': 'PCEPI',
                'PPI (Producer Inflation)': 'PPIFIS',
                'Fed Funds Rate (FOMC)': 'FEDFUNDS'
            }
            
            # Fetch macro event data
            @st.cache_data(ttl=3600)  # Cache for 1 hour
            def fetch_macro_event_data(start_date: str = "2018-01-01", end_date: str = None):
                """Fetch macro event data from FRED."""
                try:
                    from fredapi import Fred
                    
                    # Use today's date if end_date not provided
                    if end_date is None:
                        end_date = datetime.now().strftime("%Y-%m-%d")
                    
                    fred = Fred(api_key=FRED_API_KEY)
                    
                    data_dict = {}
                    for name, s_id in MACRO_EVENT_SERIES.items():
                        # Fetch data with explicit start and end dates to ensure latest data
                        series = fred.get_series(s_id, start=start_date, end=end_date)
                        
                        # Calculate YoY % change for inflation metrics (except for Fed Rate)
                        if s_id != 'FEDFUNDS':
                            data_dict[name] = series.pct_change(periods=12) * 100
                        else:
                            data_dict[name] = series  # The interest rate is already a percentage
                    
                    # Combine into a single DataFrame and filter for recent history
                    df = pd.DataFrame(data_dict).dropna().loc[start_date:]
                    return df
                except ImportError:
                    return pd.DataFrame()
                except Exception as e:
                    st.error(f"Error fetching macro event data: {str(e)}")
                    return pd.DataFrame()
            
            with st.spinner('🔄 Fetching inflation and Fed rate data from FRED...'):
                macro_event_df = fetch_macro_event_data()
            
            if macro_event_df.empty:
                st.warning("⚠️ Unable to fetch macro event data. Please ensure `fredapi` is installed: `pip install fredapi`")
            else:
                # Summary metrics
                st.markdown("#### 📊 Current Values")
                
                if not macro_event_df.empty:
                    cols = st.columns(4)
                    last_row = macro_event_df.iloc[-1]
                    
                    metrics_data = [
                        ("CPI (Consumer Inflation)", last_row.get("CPI (Consumer Inflation)", float("nan"))),
                        ("PCE (Fed Target Inflation)", last_row.get("PCE (Fed Target Inflation)", float("nan"))),
                        ("PPI (Producer Inflation)", last_row.get("PPI (Producer Inflation)", float("nan"))),
                        ("Fed Funds Rate (FOMC)", last_row.get("Fed Funds Rate (FOMC)", float("nan"))),
                    ]
                    
                    for idx, (label, value) in enumerate(metrics_data):
                        with cols[idx]:
                            if not pd.isna(value):
                                if "Fed Funds Rate" in label:
                                    st.metric(label, f"{value:.2f}%")
                                else:
                                    st.metric(label, f"{value:.2f}% YoY")
                            else:
                                st.metric(label, "N/A")
                
                st.markdown("---")
                
                # Individual charts for each indicator
                st.markdown("#### 📈 Individual Indicator Charts")
                
                for indicator_name in MACRO_EVENT_SERIES.keys():
                    if indicator_name in macro_event_df.columns:
                        indicator_df = pd.DataFrame({indicator_name: macro_event_df[indicator_name]})
                        chart = create_macro_event_chart(indicator_df, indicator_name)
                        st.plotly_chart(chart, use_container_width=True)
                        st.markdown("---")
                
                # Data table
                st.markdown("#### 📋 Detailed Data Table")
                st.caption("Historical data for all inflation and Fed rate indicators")
                
                if not macro_event_df.empty:
                    display_df = macro_event_df.tail(100).copy()  # Last 100 data points
                    display_df.index.name = "Date"
                    
                    # Format the dataframe for display
                    styled_df = display_df.style.format({
                        "CPI (Consumer Inflation)": "{:.2f}%",
                        "PCE (Fed Target Inflation)": "{:.2f}%",
                        "PPI (Producer Inflation)": "{:.2f}%",
                        "Fed Funds Rate (FOMC)": "{:.2f}%",
                    })
                    
                    st.dataframe(styled_df, use_container_width=True, height=400)
                
                # Info expander
                with st.expander("📖 Inflation & Fed Rate Guide", expanded=False):
                    st.markdown(
                        """
                        | Indicator | FRED Code | Description |
                        |-----------|-----------|-------------|
                        | **CPI** | CPIAUCSL | Consumer Price Index - measures consumer inflation (YoY %) |
                        | **PCE** | PCEPI | Personal Consumption Expenditures - Fed's preferred inflation measure (YoY %) |
                        | **PPI** | PPIFIS | Producer Price Index - measures producer/inflation at wholesale level (YoY %) |
                        | **Fed Funds Rate** | FEDFUNDS | Federal Funds Rate - interest rate set by FOMC (%) |
                        
                        **Key Concepts:**
                        - **CPI (Consumer Inflation)**: Measures price changes for consumer goods/services
                        - **PCE (Fed Target Inflation)**: Fed's preferred measure, typically lower than CPI
                        - **PPI (Producer Inflation)**: Leading indicator, measures wholesale price changes
                        - **Fed Funds Rate**: Interest rate banks charge each other, set by Federal Reserve
                        
                        **Interpretation:**
                        - **High Inflation (>2-3%)**: Erodes purchasing power, may trigger Fed rate hikes
                        - **Low Inflation (<2%)**: May indicate weak demand, Fed may lower rates
                        - **Fed Rate Hikes**: Typically used to combat inflation, can slow economic growth
                        - **Fed Rate Cuts**: Typically used to stimulate economy, can increase inflation
                        
                        **Historical Context:**
                        - Fed targets 2% PCE inflation over the long run
                        - CPI typically runs 0.3-0.5% higher than PCE
                        - PPI often leads CPI by 1-3 months
                        - Yield curve inversions often follow Fed rate hiking cycles
                        """
                    )

    # =============================================================================
    # TAB 8: TREASURY YIELDS
    # =============================================================================
    with tab_treasury:
        st.markdown("### 📊 Treasury Yields Dashboard")
        st.caption("US Treasury yield curve analysis: 3M, 2Y, 5Y, 10Y yields and 10Y-2Y spread with inversion tracking")
        
        # Fetch treasury data
        @st.cache_data(ttl=3600)  # Cache for 1 hour
        def fetch_treasury_data(start_date: str, weekly: bool = False):
            """Fetch treasury yield data."""
            try:
                end_date = pd.Timestamp.today().strftime("%Y-%m-%d")
                df = fetch_treasury_yields(start_date, end_date)
                
                if weekly:
                    # Friday weekly frequency; last observed value in the week
                    df = df.resample("W-FRI").last().ffill()
                
                # Compute spread
                if "10Y" in df.columns and "2Y" in df.columns:
                    df["10Y-2Y"] = df["10Y"] - df["2Y"]
                
                return df
            except Exception as e:
                st.error(f"Error fetching treasury data: {str(e)}")
                return pd.DataFrame()
        
        with st.spinner('🔄 Fetching treasury yield data...'):
            # Use default values: start date 2015-01-01, no weekly resample
            treasury_df = fetch_treasury_data("2015-01-01", False)
        
        if treasury_df.empty:
            st.warning("⚠️ Unable to fetch treasury yield data. Please try again later.")
            st.info("💡 **Note:** Treasury yield data requires `pandas_datareader` package. Install with: `pip install pandas_datareader`")
        else:
            # Summary metrics
            st.markdown("#### 📊 Current Yield Values")
            
            if all(col in treasury_df.columns for col in ["3M", "2Y", "5Y", "10Y"]):
                cols = st.columns(4)
                last_row = treasury_df.dropna(subset=["3M", "2Y", "5Y", "10Y"]).iloc[-1] if not treasury_df.empty else None
                
                if last_row is not None:
                    metrics_data = [
                        ("3M", last_row.get("3M", float("nan"))),
                        ("2Y", last_row.get("2Y", float("nan"))),
                        ("5Y", last_row.get("5Y", float("nan"))),
                        ("10Y", last_row.get("10Y", float("nan"))),
                    ]
                    
                    for idx, (label, value) in enumerate(metrics_data):
                        with cols[idx]:
                            if not pd.isna(value):
                                st.metric(f"{label} Yield", f"{value:.2f}%")
                            else:
                                st.metric(f"{label} Yield", "N/A")
            
            st.markdown("---")
            
            # Yield curve chart
            st.markdown("#### 📈 Treasury Yield Curve")
            st.caption(
                "Interactive chart showing the evolution of US Treasury yields across different maturities. "
                "The yield curve reflects market expectations for interest rates and economic conditions. "
                "An inverted yield curve (short-term yields higher than long-term) often signals economic recession risk."
            )
            
            yields_chart = create_treasury_yields_chart(treasury_df[["3M", "2Y", "5Y", "10Y"]] if all(col in treasury_df.columns for col in ["3M", "2Y", "5Y", "10Y"]) else treasury_df)
            st.plotly_chart(yields_chart, use_container_width=True)
            
            st.markdown("---")
            
            # Spread chart
            if "10Y" in treasury_df.columns and "2Y" in treasury_df.columns:
                st.markdown("#### 📉 10Y-2Y Spread Analysis")
                st.caption(
                    "The 10Y-2Y spread is a key indicator of yield curve shape. "
                    "**Positive spread (normal curve)**: Long-term rates higher than short-term - typical healthy economy. "
                    "**Negative spread (inverted curve)**: Short-term rates higher than long-term - often precedes recessions. "
                    "The red shaded areas indicate periods of inversion."
                )
                
                spread_chart = create_treasury_spread_chart(treasury_df[["2Y", "10Y"]])
                st.plotly_chart(spread_chart, use_container_width=True)
                
                # Spread status
                if "10Y-2Y" in treasury_df.columns:
                    last_spread = treasury_df["10Y-2Y"].dropna().iloc[-1] if not treasury_df["10Y-2Y"].dropna().empty else None
                    if last_spread is not None:
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            if last_spread < 0:
                                st.error(f"🔴 **CURVE INVERTED** - Spread: {last_spread:.2f} pp")
                                st.caption("The yield curve is currently inverted, which historically has been a recession warning signal.")
                            else:
                                st.success(f"🟢 **CURVE NORMAL** - Spread: {last_spread:.2f} pp")
                                st.caption("The yield curve is in a normal state with long-term rates above short-term rates.")
                        with col2:
                            spread_change = treasury_df["10Y-2Y"].dropna().iloc[-1] - treasury_df["10Y-2Y"].dropna().iloc[-2] if len(treasury_df["10Y-2Y"].dropna()) > 1 else 0
                            if spread_change > 0:
                                st.info(f"📈 **Steepening** - Spread increased by {spread_change:.2f} pp")
                            elif spread_change < 0:
                                st.warning(f"📉 **Flattening** - Spread decreased by {abs(spread_change):.2f} pp")
                            else:
                                st.info("➡️ **Stable** - No change in spread")
            
            st.markdown("---")
            
            # Data table
            with st.expander("📋 Detailed Yield Data (Last 30 Days)", expanded=False):
                if not treasury_df.empty:
                    display_df = treasury_df.tail(30).copy()
                    display_df.index.name = "Date"
                    st.dataframe(
                        display_df.style.format({
                            "3M": "{:.2f}%",
                            "2Y": "{:.2f}%",
                            "5Y": "{:.2f}%",
                            "10Y": "{:.2f}%",
                            "10Y-2Y": "{:.2f} pp",
                        }) if "10Y-2Y" in display_df.columns else display_df.style.format({
                            "3M": "{:.2f}%",
                            "2Y": "{:.2f}%",
                            "5Y": "{:.2f}%",
                            "10Y": "{:.2f}%",
                        }),
                        use_container_width=True,
                    )
            
            # Info expander
            with st.expander("📖 Treasury Yields Guide", expanded=False):
                st.markdown(
                    """
                    | Maturity | FRED Code | Description |
                    |----------|-----------|-------------|
                    | **3M** | DGS3MO | 3-Month Treasury Bill Rate |
                    | **2Y** | DGS2 | 2-Year Treasury Note Rate |
                    | **5Y** | DGS5 | 5-Year Treasury Note Rate |
                    | **10Y** | DGS10 | 10-Year Treasury Note Rate |
                    
                    **Key Concepts:**
                    - **Yield Curve**: Graph showing yields across different maturities
                    - **Normal Curve**: Upward sloping (long-term > short-term) - healthy economy
                    - **Inverted Curve**: Downward sloping (short-term > long-term) - recession warning
                    - **10Y-2Y Spread**: Difference between 10-year and 2-year yields
                    - **Steepening**: Spread increasing (economic expansion expected)
                    - **Flattening**: Spread decreasing (economic slowdown expected)
                    
                    **Historical Context:**
                    - Yield curve inversions have preceded every US recession since 1955
                    - Inversion typically occurs 6-18 months before recession
                    - The 10Y-2Y spread is one of the most watched economic indicators
                    """
                )

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

