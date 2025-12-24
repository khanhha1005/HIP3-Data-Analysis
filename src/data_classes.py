"""
Data classes for Voyager Dashboard
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MarketSnapshot:
    ticker: str
    coin: str
    price: float
    high_24h: float
    low_24h: float
    volume_24h: float
    chg_4h: float
    chg_24h: float
    chg_7d: float
    chg_30d: float
    market_cap: Optional[float] = None
    fdv: Optional[float] = None


@dataclass
class TechnicalMetrics:
    ticker: str
    rsi14: float
    macd: float
    macd_signal: float
    macd_hist: float
    sma50: float
    sma200: float
    ema50: float
    ema200: float
    trend_state: str
    golden_cross: bool
    death_cross: bool
    vol_24h: float


@dataclass
class DerivativesMetrics:
    ticker: str
    coin: str
    latest_funding_annualized: Optional[float]
    mean_funding_annualized: Optional[float]
    max_funding_annualized: Optional[float]
    min_funding_annualized: Optional[float]
    funding_comment: str
    estimated_long_ratio: float
    estimated_short_ratio: float


@dataclass
class OptionsMetrics:
    ticker: str
    expiry: str
    spot: float
    max_pain: float
    gex_flip: Optional[float]
    atm_iv: float
    skew_25d: float

