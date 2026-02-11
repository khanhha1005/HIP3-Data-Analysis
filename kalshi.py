"""
Kalshi prediction markets integration using the Kalshi public API.
https://docs.kalshi.com/
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Company/ETF aliases for search matching (subset of llm_predictions.COMPANY_ALIASES)
COMPANY_ALIASES: Dict[str, List[str]] = {
    "AAPL": ["Apple", "Apple Inc"],
    "AMZN": ["Amazon", "Amazon.com"],
    "GOOGL": ["Alphabet", "Google"],
    "META": ["Meta", "Facebook"],
    "MSFT": ["Microsoft"],
    "NVDA": ["NVIDIA", "Nvidia"],
    "TSLA": ["Tesla"],
    "NFLX": ["Netflix"],
    "COIN": ["Coinbase"],
    "ORCL": ["Oracle"],
}


def fetch_events(
    status: str = "open",
    with_nested_markets: bool = True,
    limit: int = 200,
    cursor: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch events from Kalshi public API.
    No authentication required.
    """
    url = f"{KALSHI_API_BASE}/events"
    params = {
        "status": status,
        "with_nested_markets": str(with_nested_markets).lower(),
        "limit": limit,
    }
    if cursor:
        params["cursor"] = cursor

    all_events: List[Dict[str, Any]] = []
    while True:
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            events = data.get("events") or []
            all_events.extend(events)
            cursor = data.get("cursor")
            if not cursor or not events:
                break
            params["cursor"] = cursor
            time.sleep(0.1)  # Rate limit
        except requests.RequestException as e:
            raise RuntimeError(f"Kalshi API error: {e}") from e
    return all_events


def extract_yes_probability(market: Dict[str, Any]) -> Optional[float]:
    """Extract YES probability from Kalshi market (0-1)."""
    # last_price is in cents (0-100)
    last_price = market.get("last_price")
    if last_price is not None:
        try:
            p = float(last_price) / 100.0
            return min(1.0, max(0.0, p))
        except (TypeError, ValueError):
            pass
    # Fallback to yes_ask_dollars or yes_bid_dollars
    for key in ("yes_ask_dollars", "yes_bid_dollars", "last_price_dollars"):
        val = market.get(key)
        if val is not None:
            try:
                p = float(val)
                return min(1.0, max(0.0, p))
            except (TypeError, ValueError):
                pass
    return None


def event_matches_ticker(event: Dict[str, Any], ticker: str) -> bool:
    """Check if event title/subtitle/series/markets mention the ticker or aliases."""
    ticker_upper = ticker.upper()
    search_terms = [ticker_upper, ticker.lower()]
    aliases = COMPANY_ALIASES.get(ticker_upper, [])
    for a in aliases:
        search_terms.extend([a, a.lower()])

    def text_contains(text: str) -> bool:
        if not text:
            return False
        t = str(text).lower()
        for s in search_terms:
            if s.lower() in t:
                return True
        return False

    if text_contains(event.get("title")):
        return True
    if text_contains(event.get("sub_title")):
        return True
    if text_contains(event.get("series_ticker")):
        return True
    for m in event.get("markets") or []:
        if text_contains(m.get("title")):
            return True
        if text_contains(m.get("subtitle")):
            return True
    return False


def filter_events_by_tickers(
    events: List[Dict[str, Any]],
    tickers: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Filter events by ticker, return {ticker: [events]}."""
    result: Dict[str, List[Dict[str, Any]]] = {t: [] for t in tickers}
    for event in events:
        for ticker in tickers:
            if event_matches_ticker(event, ticker):
                result[ticker].append(event)
    return result


def market_target_label(market: Dict[str, Any]) -> str:
    """Get display label for a market."""
    return (
        market.get("title")
        or market.get("subtitle")
        or market.get("yes_sub_title")
        or market.get("ticker")
        or "Unknown"
    )
