"""
Utility functions for Voyager Dashboard
"""

import json
import math
from typing import Any, Dict


def extract_ticker(symbol: str) -> str:
    """Extract ticker from symbol (handles xyz:, flx:, vntl: prefixes)."""
    if ":" in symbol:
        return symbol.split(":")[-1]
    return symbol


def _cache_key(payload: Dict[str, Any]) -> str:
    """Generate cache key from payload."""
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return s  # Return string for hashing if needed


def format_pct(value: float, decimals: int = 2) -> str:
    """Format a percentage value with color coding."""
    if math.isnan(value):
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_currency(value: float, decimals: int = 2) -> str:
    """Format a currency value."""
    if math.isnan(value):
        return "N/A"
    return f"${value:,.{decimals}f}"

