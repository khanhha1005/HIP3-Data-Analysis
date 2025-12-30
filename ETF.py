import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- 1. Configuration & Data Fetching ---
st.set_page_config(page_title="ETF Flow & Demand Dashboard", layout="wide")
st.title("📊 ETF Flow & Demand Dashboard")
st.markdown("Analysis of **FNGS, XLG, QQQ, and MGK** to understand institutional demand drivers.")

tickers = ['FNGS', 'XLG', 'QQQ', 'MGK']
issuer_map = {
    'FNGS': 'MicroSectors (BMO)',
    'XLG': 'Invesco (Top 50)',
    'QQQ': 'Invesco (Nasdaq)',
    'MGK': 'Vanguard (Mega Cap)'
}

@st.cache_data
def fetch_and_process_data(tickers, period="1y"):
    """Fetches data from yfinance and calculates flow metrics."""
    data = yf.download(tickers, period=period, group_by='ticker', auto_adjust=True)
    processed_data = {}
    summary_list = []

    for ticker in tickers:
        try:
            df = data[ticker].copy()
            if df.empty:
                st.warning(f"No data found for {ticker}")
                continue
        except KeyError:
            st.error(f"Data not found for {ticker}")
            continue

        # --- Calculate Flow Proxy ---
        # Estimated Daily Flow = Close Price * Volume * Direction (+/-)
        df['Price_Change'] = df['Close'].diff()
        df['Direction'] = np.sign(df['Price_Change'])
        # Forward-fill direction for days with no price change
        df['Direction'] = df['Direction'].replace(0, method='ffill')
        df['Daily_Flow_Est'] = df['Close'] * df['Volume'] * df['Direction']

        # --- Calculate Weekly Flow ---
        weekly_flow = df['Daily_Flow_Est'].resample('W').sum()
        current_weekly_flow = weekly_flow.iloc[-1] if not weekly_flow.empty else 0

        # --- Calculate Flow Streak ---
        # Simple definition: Count consecutive days with money flow in the same direction
        # Positive flow = Buy, Negative flow = Sell
        # If today's flow is positive, yesterday was also positive, and the day before was also positive → Streak = +3
        # If today's flow is negative but yesterday was positive → Streak breaks, reset to -1
        df['Flow_Sign'] = np.sign(df['Daily_Flow_Est'])
        # Replace 0 with previous sign (forward fill), then backward fill for any remaining 0s
        df['Flow_Sign'] = df['Flow_Sign'].replace(0, method='ffill').replace(0, method='bfill')
        # If still 0 (all values were 0), default to 1
        df['Flow_Sign'] = df['Flow_Sign'].replace(0, 1)
        
        # Calculate streak: count consecutive days with same sign
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
                
                sign = int(sign)  # Ensure it's an integer (-1, 0, or 1)
                
                if current_sign is None or sign != current_sign:
                    # Streak breaks or starts - reset to 1 with new sign
                    current_sign = sign
                    current_streak = 1
                else:
                    # Continue streak
                    current_streak += 1
                
                # Apply sign to streak (positive for buying, negative for selling)
                streak_values.append(int(current_streak * sign))
            
            df['Streak'] = streak_values
            streak_val = int(df['Streak'].iloc[-1]) if not df.empty and len(df['Streak']) > 0 else 0
        else:
            df['Streak'] = 0
            streak_val = 0

        # --- Calculate Acceleration (Simplified) ---
        # Compare the latest daily flow to the 20-day moving average
        df['Flow_MA20'] = df['Daily_Flow_Est'].rolling(window=20).mean()
        if not df.empty and not pd.isna(df['Flow_MA20'].iloc[-1]):
            acceleration = df['Daily_Flow_Est'].iloc[-1] - df['Flow_MA20'].iloc[-1]
            acc_status = "SPEEDING UP" if acceleration > 0 else "SLOWING DOWN"
        else:
            acc_status = "N/A"

        # --- Normalize Price for Comparison ---
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
            # Calculate total absolute flow for determining dominance
            'Total_Flow_Abs': df['Daily_Flow_Est'].abs().sum() if not df.empty else 0
        })
    
    summary_df = pd.DataFrame(summary_list)
    return processed_data, summary_df

# --- Sidebar for User Input ---
with st.sidebar:
    st.header("⚙️ Settings")
    period = st.selectbox("Select Time Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
    st.markdown("---")
    st.markdown("**Note:** Flow data is a proxy based on Price × Volume.")

# --- Fetch Data ---
with st.spinner('Fetching and processing data...'):
    processed_data, summary_df = fetch_and_process_data(tickers, period)

# --- 2. Dashboard Layout & Visualizations ---

# --- Row 1: Summary & Dominant Issuer ---
st.header("📝 Summary Metrics")
if not summary_df.empty:
    # Determine Dominant Issuer based on total absolute flow volume
    dominant_issuer = summary_df.sort_values(by='Total_Flow_Abs', ascending=False).iloc[0]
    st.markdown(f"🏆 **Dominant Issuer (Total Flow Volume):** {dominant_issuer['Issuer']} ({dominant_issuer['Ticker']})")
    # Display summary table, formatting price and dropping the helper column
    st.dataframe(summary_df.drop(columns=['Total_Flow_Abs']).style.format({"Price": "${:.2f}"}), use_container_width=True)
else:
    st.write("No data available to display summary.")

st.markdown("---")

# --- Row 1.5: Detailed 20-Day Table ---
st.header("📊 Detailed 20-Day Flow Analysis")
st.markdown("""
**Streak Definition:** Counts consecutive days with money flow in the same direction (Buy or Sell).
- **Positive numbers (e.g., +5, +10):** Consecutive days of buying (institutional accumulation)
- **Negative numbers (e.g., -3, -7):** Consecutive days of selling (institutional distribution)
- **Small numbers (e.g., +1, -1, +2):** Market is sideways, no clear trend
""")

for ticker in tickers:
    if ticker not in processed_data:
        continue
    
    df = processed_data[ticker]
    if df.empty:
        continue
    
    st.markdown(f"### {ticker} - Last 20 Days")
    
    # Get last 20 days
    df_last_20 = df.tail(20).copy()
    
    # Create detailed table
    detail_table = pd.DataFrame({
        'Date': df_last_20.index.strftime('%Y-%m-%d'),
        'Price': df_last_20['Close'].round(2),
        'Volume': df_last_20['Volume'].apply(lambda x: f"{x:,.0f}"),
        'Daily Flow ($M)': (df_last_20['Daily_Flow_Est'] / 1_000_000).round(2),
        'Streak (Days)': df_last_20['Streak'].astype(int),
    })
    
    # Format the table
    styled_table = detail_table.style.format({
        'Price': '${:.2f}',
        'Daily Flow ($M)': '${:.2f}M',
    })
    
    st.dataframe(styled_table, use_container_width=True, hide_index=True)
    
    st.markdown("---")

# --- Row 2: Performance & Flow Plots ---
st.header("📈 Performance & Flow Analysis")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Relative Performance (Rebased to 100)")
    fig_perf = go.Figure()
    for ticker in tickers:
        if ticker in processed_data:
            df = processed_data[ticker]
            fig_perf.add_trace(go.Scatter(x=df.index, y=df['Norm_Price'], mode='lines', name=ticker))
    fig_perf.update_layout(yaxis_title="Growth (%)", hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig_perf, use_container_width=True)

with col2:
    st.subheader("Estimated Institutional Money Flow (Daily)")
    fig_flow = go.Figure()
    for ticker in tickers:
        if ticker in processed_data:
            df = processed_data[ticker]
            # Plot daily flow in millions
            fig_flow.add_trace(go.Scatter(x=df.index, y=df['Daily_Flow_Est'] / 1_000_000, mode='lines', name=ticker))
    fig_flow.add_hline(y=0, line_dash="dash", line_color="black")
    fig_flow.update_layout(yaxis_title="Estimated Flow ($ Millions)", hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig_flow, use_container_width=True)

# --- Row 3: Flow Trend & Correlation ---
st.header("🔄 Flow Trend & Correlation")
col3, col4 = st.columns(2)

with col3:
    st.subheader("Flow Trend (20-Day Moving Average)")
    st.markdown("Shows the smoothed direction of money flow, reducing daily noise.")
    fig_flow_trend = go.Figure()
    for ticker in tickers:
        if ticker in processed_data:
            df = processed_data[ticker]
            # Plot 20-day moving average of flow in millions
            fig_flow_trend.add_trace(go.Scatter(x=df.index, y=df['Flow_MA20'] / 1_000_000, mode='lines', name=ticker))
    fig_flow_trend.add_hline(y=0, line_dash="dash", line_color="black")
    fig_flow_trend.update_layout(yaxis_title="Estimated Flow Trend ($ Millions)", hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig_flow_trend, use_container_width=True)

with col4:
    st.subheader("Correlation Matrix (Close Price)")
    st.markdown("Measures how closely the ETFs' prices move together (1.0 = identical).")
    # Create a DataFrame of close prices for correlation calculation
    close_prices = pd.DataFrame({t: processed_data[t]['Close'] for t in tickers if t in processed_data})
    if not close_prices.empty:
        corr_matrix = close_prices.corr()
        # Create a heatmap using Plotly Express
        fig_corr = px.imshow(corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
        fig_corr.update_layout(template="plotly_white")
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.write("No price data available for correlation analysis.")

# --- Row 4: Volatility Analysis ---
st.header("⚠️ Volatility Profile (Risk)")
vol_data = []
for ticker in tickers:
    if ticker in processed_data:
        df = processed_data[ticker]
        # Calculate annualized volatility
        daily_ret = df['Close'].pct_change().dropna()
        ann_vol = daily_ret.std() * (252 ** 0.5) * 100
        vol_data.append({'Ticker': ticker, 'Annualized Volatility (%)': ann_vol})

if vol_data:
    vol_df = pd.DataFrame(vol_data)
    # Create a bar chart for volatility comparison
    fig_vol = px.bar(vol_df, x='Ticker', y='Annualized Volatility (%)', color='Ticker', title="Annualized Volatility", text_auto='.1f')
    fig_vol.update_layout(template="plotly_white", showlegend=False)
    fig_vol.update_traces(textposition='outside')
    st.plotly_chart(fig_vol, use_container_width=True)
else:
    st.write("No data available for volatility analysis.")