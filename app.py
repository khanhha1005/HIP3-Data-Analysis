"""
Voyager HIP-3 Equity Perps Dashboard
Main entry point for Streamlit application
"""

import math
import time
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

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
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
        
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #16161f;
            --border-color: #1e1e2e;
            --accent: #fbbf24;
            --accent-glow: #f59e0b;
            --green: #22c55e;
            --red: #ef4444;
            --blue: #3b82f6;
            --purple: #a855f7;
            --cyan: #06b6d4;
            --text: #e4e4e7;
            --text-muted: #71717a;
        }
        
        .stApp {
            background: linear-gradient(180deg, var(--bg-primary) 0%, #0f0f18 100%);
            font-family: 'Space Grotesk', sans-serif;
        }
        
        /* Header styling */
        .main-header {
            text-align: center;
            padding: 30px 0;
            margin-bottom: 20px;
            background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
            border-radius: 20px;
            border: 1px solid rgba(251, 191, 36, 0.2);
        }
        
        .main-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(90deg, #fbbf24, #f59e0b, #fbbf24);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradient-shift 3s ease infinite;
            margin-bottom: 8px;
            letter-spacing: 2px;
        }
        
        @keyframes gradient-shift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .subtitle {
            color: var(--text-muted);
            font-size: 1rem;
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Metrics styling */
        div[data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.4rem;
            font-weight: 600;
        }
        
        div[data-testid="stMetricLabel"] {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        
        .stMetric {
            background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: 8px;
            padding: 12px 24px;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(251, 191, 36, 0.1);
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-glow) 100%) !important;
            color: #000 !important;
            box-shadow: 0 0 20px rgba(251, 191, 36, 0.4);
        }
        
        /* Card styling */
        .info-card {
            background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid var(--border-color);
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }
        
        .card-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            border-right: 1px solid var(--border-color);
        }
        
        section[data-testid="stSidebar"] .stMarkdown h3 {
            font-family: 'Space Grotesk', sans-serif;
            color: var(--accent);
        }
        
        /* Dataframe styling */
        .stDataFrame {
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background: var(--bg-card);
            border-radius: 12px;
            font-family: 'Space Grotesk', sans-serif;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--accent);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-glow);
        }
        
        /* Alert boxes */
        .stSuccess, .stInfo, .stWarning, .stError {
            border-radius: 12px;
            font-family: 'JetBrains Mono', monospace;
        }
        
        h1, h2, h3, h4 {
            font-family: 'Space Grotesk', sans-serif !important;
        }
        
        code {
            font-family: 'JetBrains Mono', monospace !important;
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
            <div class="subtitle">HIP-3 Equity Perpetuals Analytics Dashboard</div>
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
    tab_overview, tab_technicals, tab_derivatives, tab_options = st.tabs(
        ["📈 Market Snapshot", "📊 Technical Analysis", "🔥 Derivatives Intel", "📉 Options Analytics"]
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
                    st.plotly_chart(create_rsi_chart(df, tech["rsi_series"], ticker), use_container_width=True, key=f"rsi_{ticker}")

            with chart_col2:
                if "macd_series" in tech:
                    st.plotly_chart(
                        create_macd_chart(df, tech["macd_series"], tech["signal_series"], tech["hist_series"], ticker),
                        use_container_width=True,
                        key=f"macd_{ticker}",
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

