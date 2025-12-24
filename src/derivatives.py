"""
Derivatives functions for Voyager Dashboard
"""

import math
from typing import Dict

import numpy as np
import pandas as pd

from src.data_classes import DerivativesMetrics
from src.utils import extract_ticker


def compute_derivatives_metrics(coin: str, funding_df: pd.DataFrame) -> DerivativesMetrics:
    """Compute derivatives metrics from funding history."""
    ticker = extract_ticker(coin)

    if funding_df.empty:
        return DerivativesMetrics(
            ticker=ticker,
            coin=coin,
            latest_funding_annualized=None,
            mean_funding_annualized=None,
            max_funding_annualized=None,
            min_funding_annualized=None,
            funding_comment="No funding data available.",
            estimated_long_ratio=0.5,
            estimated_short_ratio=0.5,
        )

    # Infer funding interval from timestamps
    if len(funding_df) >= 2:
        times = funding_df["time"].sort_values()
        diffs = times.diff().dropna().dt.total_seconds() / 3600
        interval_hours = float(diffs.median()) if len(diffs) > 0 else 1.0
    else:
        interval_hours = 1.0

    annual_factor = 24.0 * 365.0 / max(interval_hours, 0.1)

    funding_df = funding_df.copy()
    funding_df["annualized"] = funding_df["funding_rate"] * annual_factor

    # Calculate annualized funding rate from MEAN of historical data
    # This is more representative than just the latest value
    mean_funding_rate = float(funding_df["funding_rate"].mean())
    annualized_from_historical = mean_funding_rate * annual_factor
    
    max_val = float(funding_df["annualized"].max())
    min_val = float(funding_df["annualized"].min())
    
    # Also track latest for comparison
    latest_raw = float(funding_df["funding_rate"].iloc[-1])

    # Generate funding comment based on annualized historical average
    if not math.isfinite(annualized_from_historical):
        comment = "Funding data unavailable."
    elif annualized_from_historical > 0.5:
        comment = f"Extremely high positive funding ({annualized_from_historical:.1%} ann avg): crowded longs, correction risk."
    elif annualized_from_historical > 0.1:
        comment = f"Moderately positive funding ({annualized_from_historical:.1%} ann avg): bullish positioning."
    elif annualized_from_historical < -0.5:
        comment = f"Deeply negative funding ({annualized_from_historical:.1%} ann avg): shorts crowded, squeeze risk."
    elif annualized_from_historical < -0.1:
        comment = f"Moderately negative funding ({annualized_from_historical:.1%} ann avg): bearish skew."
    else:
        comment = f"Funding near neutral ({annualized_from_historical:.1%} ann avg): balanced positioning."

    # Estimate long/short ratio from historical funding data
    # Use mean funding rate for stable estimation
    if abs(mean_funding_rate) > 0.0000001:
        # Scale funding rate to long/short ratio
        # Typical funding rates are small (0.0001 = 0.01%)
        # Map to 0.2-0.8 range for reasonable display
        normalized = np.tanh(mean_funding_rate * 5000)  # tanh for bounded output
        estimated_long_ratio = 0.5 + (normalized * 0.3)  # 0.2 to 0.8 range
        estimated_long_ratio = max(0.2, min(0.8, estimated_long_ratio))
    else:
        estimated_long_ratio = 0.5

    return DerivativesMetrics(
        ticker=ticker,
        coin=coin,
        latest_funding_annualized=annualized_from_historical,  # Now using historical average
        mean_funding_annualized=annualized_from_historical,
        max_funding_annualized=max_val,
        min_funding_annualized=min_val,
        funding_comment=comment,
        estimated_long_ratio=estimated_long_ratio,
        estimated_short_ratio=1.0 - estimated_long_ratio,
    )

