"""
Chart creation functions for Voyager Dashboard
"""

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go

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
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=450,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
            fillcolor="rgba(0, 212, 255, 0.15)",
        )
    )

    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["red"], annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["green"], annotation_text="Oversold")
    fig.add_hline(y=50, line_dash="dot", line_color=COLORS["gray"])

    fig.update_layout(
        template="plotly_dark",
        yaxis=dict(range=[0, 100]),
        height=220,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
        template="plotly_dark",
        height=220,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
        template="plotly_dark",
        height=180,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
        template="plotly_dark",
        height=280,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_tickformat=".1%",
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
            line=dict(color="rgba(255, 255, 255, 0.2)", width=2)
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
        template="plotly_dark",
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
            line=dict(color="rgba(255, 255, 255, 0.2)", width=2)
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
        template="plotly_dark",
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
            fillcolor="rgba(0, 212, 255, 0.15)",
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
        template="plotly_dark",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Time",
        yaxis_title="Volatility",
        yaxis_tickformat=".0%",
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
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
        template="plotly_dark",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Strike Price",
        yaxis_title="Implied Volatility",
        yaxis_tickformat=".0%",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(15, 15, 35, 0)",
        plot_bgcolor="rgba(15, 15, 35, 0)",
        font=dict(family="JetBrains Mono, monospace"),
    )
    
    return fig

