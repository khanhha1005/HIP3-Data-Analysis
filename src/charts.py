"""
Chart creation functions for Voyager Dashboard
"""

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import COLORS


def create_price_chart(df: pd.DataFrame, ticker: str, ma: Dict[str, pd.Series]) -> go.Figure:
    """Create an interactive price chart with moving averages."""
    fig = go.Figure()

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color=COLORS["green"],
            decreasing_line_color=COLORS["red"],
        )
    )

    # Moving averages
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=ma["sma50"],
            name="SMA 50",
            line=dict(color=COLORS["blue"], width=1.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=ma["sma200"],
            name="SMA 200",
            line=dict(color=COLORS["orange"], width=1.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=ma["ema50"],
            name="EMA 50",
            line=dict(color=COLORS["cyan"], width=1, dash="dot"),
        )
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        height=450,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )

    return fig


def create_rsi_chart(df: pd.DataFrame, rsi_series: pd.Series, ticker: str) -> go.Figure:
    """Create RSI chart."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=rsi_series,
            name="RSI(14)",
            line=dict(color=COLORS["purple"], width=2),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.12)",
        )
    )

    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["red"], annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["green"], annotation_text="Oversold")
    fig.add_hline(y=50, line_dash="dot", line_color=COLORS["gray"])

    fig.update_layout(
        template="plotly_white",
        yaxis=dict(range=[0, 100]),
        height=220,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )

    return fig


def create_macd_chart(
    df: pd.DataFrame,
    macd_series: pd.Series,
    signal_series: pd.Series,
    hist_series: pd.Series,
    ticker: str,
) -> go.Figure:
    """Create MACD chart."""
    fig = go.Figure()

    colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in hist_series]
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=hist_series,
            name="Histogram",
            marker_color=colors,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=macd_series,
            name="MACD",
            line=dict(color=COLORS["blue"], width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=signal_series,
            name="Signal",
            line=dict(color=COLORS["orange"], width=2),
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=220,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )

    return fig


def create_volume_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create volume chart."""
    colors = [
        COLORS["green"] if df["close"].iloc[i] >= df["open"].iloc[i] else COLORS["red"]
        for i in range(len(df))
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["time"],
            y=df["volume"],
            name="Volume",
            marker_color=colors,
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=180,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )

    return fig


def create_funding_chart(funding_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create funding rate chart."""
    if funding_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No funding data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=280, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig

    funding_df = funding_df.copy()
    funding_df["annualized"] = funding_df["funding_rate"] * 24 * 365

    colors = [
        COLORS["green"] if v >= 0 else COLORS["red"] for v in funding_df["annualized"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=funding_df["time"],
            y=funding_df["annualized"],
            name="Funding Rate",
            marker_color=colors,
        )
    )

    fig.add_hline(y=0, line_dash="solid", line_color=COLORS["gray"])

    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_tickformat=".1%",
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )

    return fig


def create_long_short_pie(long_ratio: float, ticker: str) -> go.Figure:
    """Create a pie chart for long/short ratio."""
    short_ratio = 1.0 - long_ratio
    
    fig = go.Figure(data=[go.Pie(
        labels=["Long", "Short"],
        values=[long_ratio * 100, short_ratio * 100],
        hole=0.6,
        marker=dict(
            colors=[COLORS["green"], COLORS["red"]],
            line=dict(color="rgba(0, 0, 0, 0.1)", width=2)
        ),
        textinfo="percent",
        textfont=dict(size=14, color="white", family="JetBrains Mono"),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    )])
    
    # Add center annotation
    sentiment = "LONG BIAS" if long_ratio > 0.55 else ("SHORT BIAS" if long_ratio < 0.45 else "BALANCED")
    sentiment_color = COLORS["green"] if long_ratio > 0.55 else (COLORS["red"] if long_ratio < 0.45 else COLORS["accent"])
    
    fig.add_annotation(
        text=f"<b>{sentiment}</b><br><span style='font-size:11px'>{long_ratio:.0%} Long</span>",
        x=0.5, y=0.5,
        font=dict(size=13, color=sentiment_color, family="Space Grotesk"),
        showarrow=False,
    )
    
    fig.update_layout(
        template="plotly_white",
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )

    return fig


def create_skew_pie(put_iv: float, call_iv: float, ticker: str) -> go.Figure:
    """Create a pie chart for put/call IV skew positioning."""
    # Normalize to percentages
    total = put_iv + call_iv
    if total == 0:
        put_pct = 50
        call_pct = 50
    else:
        put_pct = (put_iv / total) * 100
        call_pct = (call_iv / total) * 100
    
    fig = go.Figure(data=[go.Pie(
        labels=["Put IV (Fear)", "Call IV (Greed)"],
        values=[put_pct, call_pct],
        hole=0.6,
        marker=dict(
            colors=[COLORS["red"], COLORS["green"]],
            line=dict(color="rgba(0, 0, 0, 0.1)", width=2)
        ),
        textinfo="percent",
        textfont=dict(size=14, color="white", family="JetBrains Mono"),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    )])
    
    # Determine sentiment
    skew = put_iv - call_iv
    if skew > 0.02:
        sentiment = "FEAR"
        sentiment_color = COLORS["red"]
    elif skew < -0.02:
        sentiment = "GREED"
        sentiment_color = COLORS["green"]
    else:
        sentiment = "NEUTRAL"
        sentiment_color = COLORS["accent"]
    
    fig.add_annotation(
        text=f"<b>{sentiment}</b><br><span style='font-size:11px'>Skew: {skew:.1%}</span>",
        x=0.5, y=0.5,
        font=dict(size=13, color=sentiment_color, family="Space Grotesk"),
        showarrow=False,
    )
    
    fig.update_layout(
        template="plotly_white",
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )

    return fig


def create_historical_volatility_chart(hist_vol_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create historical volatility over time chart."""
    if hist_vol_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No volatility data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=300, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=hist_vol_df["time"],
            y=hist_vol_df["hist_vol"],
            name="Historical Volatility",
            mode="lines",
            line=dict(color=COLORS["purple"], width=2),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.12)",
        )
    )
    
    # Add mean line
    mean_vol = hist_vol_df["hist_vol"].mean()
    fig.add_hline(
        y=mean_vol,
        line_dash="dash",
        line_color=COLORS["accent"],
        annotation_text=f"Mean: {mean_vol:.1%}",
    )
    
    fig.update_layout(
        title=dict(text=f"{ticker} Historical Volatility (20-period, Annualized)", font=dict(size=14)),
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Time",
        yaxis_title="Volatility",
        yaxis_tickformat=".0%",
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )
    
    return fig


def create_iv_smile_chart(options_data: Dict[str, Any], ticker: str) -> go.Figure:
    """Create IV smile by strike chart."""
    if not options_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No IV data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=300, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig
    
    calls = options_data["calls"]
    puts = options_data["puts"]
    spot = options_data["spot"]
    
    # Create IV smile by strike
    call_iv_data = calls[["strike", "impliedVolatility"]].dropna()
    put_iv_data = puts[["strike", "impliedVolatility"]].dropna()
    
    fig = go.Figure()
    
    # Call IV curve
    fig.add_trace(
        go.Scatter(
            x=call_iv_data["strike"],
            y=call_iv_data["impliedVolatility"],
            name="Call IV",
            mode="lines+markers",
            line=dict(color=COLORS["green"], width=2),
            marker=dict(size=6),
        )
    )
    
    # Put IV curve
    fig.add_trace(
        go.Scatter(
            x=put_iv_data["strike"],
            y=put_iv_data["impliedVolatility"],
            name="Put IV",
            mode="lines+markers",
            line=dict(color=COLORS["red"], width=2),
            marker=dict(size=6),
        )
    )
    
    # Add spot price line
    fig.add_vline(
        x=spot,
        line_dash="dash",
        line_color=COLORS["accent"],
        annotation_text=f"Spot: ${spot:.0f}",
    )
    
    fig.update_layout(
        title=dict(text=f"{ticker} Implied Volatility Smile", font=dict(size=14)),
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Strike Price",
        yaxis_title="Implied Volatility",
        yaxis_tickformat=".0%",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )
    
    return fig


def create_macro_panel_chart(prices: pd.DataFrame) -> go.Figure:
    """
    Create a beautiful macro panel chart with DXY, VIX, S&P 500, Gold, and Oil.
    
    Args:
        prices: DataFrame with columns: DXY, VIX, S&P 500, Gold, Oil
        
    Returns:
        Plotly figure with subplots for each macro indicator
    """
    px = prices.sort_index().copy().ffill()
    px = px.dropna(axis=1, how="all")

    if px.shape[1] == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No macro data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=600, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig

    # Display order
    display_order = ["DXY", "VIX", "S&P 500", "Gold", "Oil"]
    cols = [c for c in display_order if c in px.columns] + [c for c in px.columns if c not in display_order]
    px = px[cols]
    n = len(cols)

    # Color palette for each indicator
    color_map = {
        "DXY": COLORS["accent"],      # Indigo (dollar index)
        "VIX": COLORS["red"],         # Red (volatility)
        "S&P 500": COLORS["green"],   # Green (equities)
        "Gold": COLORS["orange"],     # Orange (commodity)
        "Oil": COLORS["cyan"],        # Cyan (energy)
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
        color = color_map.get(col, COLORS["accent"])
        
        # Calculate percentage change for fill color
        if len(px) > 1:
            pct_change = px[col].pct_change().iloc[-1]
            fill_color = f"rgba(16, 185, 129, 0.12)" if pct_change >= 0 else f"rgba(244, 63, 94, 0.12)"
        else:
            fill_color = f"rgba(99, 102, 241, 0.12)"
        
        # Get current value and change
        current_val = px[col].iloc[-1]
        if len(px) > 1:
            prev_val = px[col].iloc[-2]
            change = current_val - prev_val
            change_pct = (change / prev_val) * 100 if prev_val != 0 else 0
        else:
            change = 0
            change_pct = 0
        
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
                              f"Change: {change:+.2f} ({change_pct:+.2f}%)<br>" +
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
            text="Macro Panel (DXY, VIX, S&P 500, Gold, Oil)",
            font=dict(size=20, family="Inter, sans-serif", color=COLORS["text"]),
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
            font=dict(size=13, family="Inter, sans-serif", color=COLORS["text"], weight=600),
            xanchor="left",
            x=0.02,
        )

    return fig


def create_treasury_yields_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a beautiful treasury yields chart showing 3M, 2Y, 5Y, 10Y yields.
    
    Args:
        df: DataFrame with columns: 3M, 2Y, 5Y, 10Y
        
    Returns:
        Plotly figure with yield curves
    """
    if df.empty or not any(col in df.columns for col in ["3M", "2Y", "5Y", "10Y"]):
        fig = go.Figure()
        fig.add_annotation(
            text="No treasury yield data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=500, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig

    fig = go.Figure()
    
    # Color mapping for each maturity
    color_map = {
        "3M": COLORS["cyan"],
        "2Y": COLORS["blue"],
        "5Y": COLORS["purple"],
        "10Y": COLORS["accent"],
    }
    
    # Add traces for each yield
    for col in ["3M", "2Y", "5Y", "10Y"]:
        if col in df.columns:
            series = df[col].dropna()
            if not series.empty:
                fig.add_trace(
                    go.Scatter(
                        x=series.index,
                        y=series,
                        name=col,
                        mode="lines",
                        line=dict(color=color_map.get(col, COLORS["accent"]), width=2.5),
                        hovertemplate=f"<b>{col}</b><br>" +
                                      "Date: %{x|%Y-%m-%d}<br>" +
                                      "Yield: %{y:.2f}%<br>" +
                                      "<extra></extra>",
                    )
                )
    
    # Get last values for annotation
    last_values = {}
    for col in ["3M", "2Y", "5Y", "10Y"]:
        if col in df.columns:
            last = df[col].dropna()
            if not last.empty:
                last_values[col] = last.iloc[-1]
    
    # Create annotation text
    if last_values:
        ann_text = "Last: " + ", ".join([f"{k}={v:.2f}%" for k, v in last_values.items()])
    else:
        ann_text = ""
    
    fig.update_layout(
        title=dict(
            text="US Treasury Yields (3M, 2Y, 5Y, 10Y)",
            font=dict(size=18, family="Inter, sans-serif", color=COLORS["text"]),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Date",
        yaxis_title="Yield (%)",
        template="plotly_white",
        height=500,
        margin=dict(l=60, r=30, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family="Inter, sans-serif"),
        ),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace", size=11),
        hovermode="x unified",
        annotations=[
            dict(
                text=ann_text,
                xref="paper",
                yref="paper",
                x=0.01,
                y=0.01,
                showarrow=False,
                font=dict(size=10, color=COLORS["text_muted"]),
                align="left",
            )
        ] if ann_text else [],
    )
    
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0, 0, 0, 0.05)",
        showline=True,
        linewidth=1,
        linecolor="rgba(0, 0, 0, 0.1)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0, 0, 0, 0.05)",
        showline=True,
        linewidth=1,
        linecolor="rgba(0, 0, 0, 0.1)",
    )
    
    return fig


def create_treasury_spread_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a beautiful 10Y-2Y spread chart with inversion highlighting.
    
    Args:
        df: DataFrame with columns: 2Y, 10Y
        
    Returns:
        Plotly figure with spread chart
    """
    if df.empty or "10Y" not in df.columns or "2Y" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No spread data available (need both 2Y and 10Y yields)",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=500, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig

    spread = df["10Y"] - df["2Y"]
    spread_clean = spread.dropna()
    
    if spread_clean.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No spread data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=500, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig
    
    fig = go.Figure()
    
    # Create positive and negative regions
    positive_mask = spread_clean >= 0
    negative_mask = spread_clean < 0
    
    # Add positive spread area
    if positive_mask.any():
        pos_spread = spread_clean[positive_mask]
        fig.add_trace(
            go.Scatter(
                x=pos_spread.index,
                y=pos_spread,
                mode="lines",
                name="Normal Spread (≥0)",
                line=dict(color=COLORS["green"], width=2.5),
                fill="tozeroy",
                fillcolor=f"rgba(16, 185, 129, 0.15)",
                hovertemplate="<b>Normal Spread</b><br>" +
                              "Date: %{x|%Y-%m-%d}<br>" +
                              "Spread: %{y:.2f} pp<br>" +
                              "<extra></extra>",
            )
        )
    
    # Add negative spread area (inversion)
    if negative_mask.any():
        neg_spread = spread_clean[negative_mask]
        fig.add_trace(
            go.Scatter(
                x=neg_spread.index,
                y=neg_spread,
                mode="lines",
                name="Inversion (Spread < 0)",
                line=dict(color=COLORS["red"], width=2.5),
                fill="tozeroy",
                fillcolor=f"rgba(244, 63, 94, 0.25)",
                hovertemplate="<b>Inverted Spread</b><br>" +
                              "Date: %{x|%Y-%m-%d}<br>" +
                              "Spread: %{y:.2f} pp<br>" +
                              "<extra></extra>",
            )
        )
    
    # Add zero line
    fig.add_hline(
        y=0.0,
        line_dash="solid",
        line_color=COLORS["gray"],
        line_width=1.5,
        annotation_text="Zero Line",
        annotation_position="right",
    )
    
    # Get last spread value and status
    last_spread = spread_clean.iloc[-1]
    status = "INVERTED" if last_spread < 0 else "NORMAL"
    status_color = COLORS["red"] if last_spread < 0 else COLORS["green"]
    
    fig.update_layout(
        title=dict(
            text="US Treasury 10Y-2Y Spread (Inversion Highlighted)",
            font=dict(size=18, family="Inter, sans-serif", color=COLORS["text"]),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Date",
        yaxis_title="Spread (percentage points)",
        template="plotly_white",
        height=500,
        margin=dict(l=60, r=30, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family="Inter, sans-serif"),
        ),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace", size=11),
        hovermode="x unified",
        annotations=[
            dict(
                text=f"Last spread: {last_spread:.2f} pp ({status})",
                xref="paper",
                yref="paper",
                x=0.01,
                y=0.01,
                showarrow=False,
                font=dict(size=11, color=status_color, weight="bold"),
                align="left",
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor=status_color,
                borderwidth=1,
                borderpad=4,
            )
        ],
    )
    
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0, 0, 0, 0.05)",
        showline=True,
        linewidth=1,
        linecolor="rgba(0, 0, 0, 0.1)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0, 0, 0, 0.05)",
        showline=True,
        linewidth=1,
        linecolor="rgba(0, 0, 0, 0.1)",
    )
    
    return fig


def create_macro_event_chart(df: pd.DataFrame, indicator_name: str) -> go.Figure:
    """
    Create a chart for a single macro event indicator (CPI, PCE, PPI, or Fed Rate).
    
    Args:
        df: DataFrame with a single column for the indicator
        indicator_name: Name of the indicator (e.g., "CPI (Consumer Inflation)")
        
    Returns:
        Plotly figure for the indicator
    """
    if df.empty or len(df.columns) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No data available for {indicator_name}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=400, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig

    col = df.columns[0]
    series = df[col].dropna()
    
    if series.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No data available for {indicator_name}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color=COLORS["text_muted"]),
        )
        fig.update_layout(template="plotly_white", height=400, paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)")
        return fig
    
    # Color mapping for each indicator
    color_map = {
        "CPI (Consumer Inflation)": COLORS["red"],
        "PCE (Fed Target Inflation)": COLORS["blue"],
        "PPI (Producer Inflation)": COLORS["purple"],
        "Fed Funds Rate (FOMC)": COLORS["accent"],
    }
    
    # Determine if it's Fed Rate (step chart) or inflation (line chart)
    is_fed_rate = "Fed Funds Rate" in indicator_name
    
    fig = go.Figure()
    
    if is_fed_rate:
        # Step chart for Fed Rate
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series,
                name=indicator_name,
                mode="lines",
                line=dict(
                    color=color_map.get(indicator_name, COLORS["accent"]),
                    width=2.5,
                    shape="hv"  # Step shape
                ),
                fill="tozeroy",
                fillcolor=f"rgba(99, 102, 241, 0.12)",
                hovertemplate=f"<b>{indicator_name}</b><br>" +
                              "Date: %{x|%Y-%m-%d}<br>" +
                              "Rate: %{y:.2f}%<br>" +
                              "<extra></extra>",
            )
        )
    else:
        # Line chart for inflation indicators
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series,
                name=indicator_name,
                mode="lines",
                line=dict(
                    color=color_map.get(indicator_name, COLORS["accent"]),
                    width=2.5
                ),
                fill="tozeroy",
                fillcolor=f"rgba(99, 102, 241, 0.12)",
                hovertemplate=f"<b>{indicator_name}</b><br>" +
                              "Date: %{x|%Y-%m-%d}<br>" +
                              "YoY Change: %{y:.2f}%<br>" +
                              "<extra></extra>",
            )
        )
    
    # Get last value
    last_val = series.iloc[-1]
    
    fig.update_layout(
        title=dict(
            text=indicator_name,
            font=dict(size=16, family="Inter, sans-serif", color=COLORS["text"]),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Date",
        yaxis_title="Percentage (%)",
        template="plotly_white",
        height=400,
        margin=dict(l=60, r=30, t=60, b=50),
        showlegend=False,
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="JetBrains Mono, monospace", size=11),
        hovermode="x unified",
        annotations=[
            dict(
                text=f"Last: {last_val:.2f}%",
                xref="paper",
                yref="paper",
                x=0.01,
                y=0.98,
                showarrow=False,
                font=dict(size=11, color=COLORS["text_muted"]),
                align="left",
                bgcolor="rgba(255, 255, 255, 0.8)",
            )
        ],
    )
    
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0, 0, 0, 0.05)",
        showline=True,
        linewidth=1,
        linecolor="rgba(0, 0, 0, 0.1)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0, 0, 0, 0.05)",
        showline=True,
        linewidth=1,
        linecolor="rgba(0, 0, 0, 0.1)",
    )
    
    return fig

