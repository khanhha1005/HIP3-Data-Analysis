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


# Keywords indicating stock market or financials (broad, not tied to tickers or price)
STOCK_MARKET_FINANCIAL_KEYWORDS = [
    "stock", "stocks", "share", "shares", "equity", "equities",
    "market", "financial", "finance", "trading", "trade",
    "index", "s&p", "sp500", "nasdaq", "dow", "vix",
    "close", "above", "below", "price", "target",
    "earnings", "revenue", "eps", "guidance",
    "fed", "federal reserve", "interest rate", "rates", "fomc",
    "treasury", "bond", "yield", "inflation", "cpi", "pce", "ppi",
    "gdp", "unemployment", "jobs", "employment",
    "volatility", "dollar", "dxy", "oil", "gold",
]


def event_is_stock_market_or_financials(event: Dict[str, Any]) -> bool:
    """
    Check if event is about stock market or financials in general.
    No ticker or price-specific filter — broad match for any stock/financial topic.
    """
    text_parts = [
        event.get("title"),
        event.get("sub_title"),
        event.get("series_ticker"),
    ]
    for m in event.get("markets") or []:
        text_parts.append(m.get("title"))
        text_parts.append(m.get("subtitle"))
        text_parts.append(m.get("yes_sub_title"))
    text = " ".join(str(x).lower() for x in text_parts if x)
    return any(kw in text for kw in STOCK_MARKET_FINANCIAL_KEYWORDS)


def fetch_stock_market_financial_events(
    status: str = "open",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch all Kalshi events that are about stock market or financials.
    No ticker or price filter — returns any event matching stock/financial keywords.

    Args:
        status: Event status filter - 'open', 'closed', 'settled', or '' for all.
        limit: Max events per page (pagination still fetches all).

    Returns:
        List of event dicts with nested markets.
    """
    events = fetch_events(
        status=status,
        with_nested_markets=True,
        limit=limit,
    )
    return [e for e in events if event_is_stock_market_or_financials(e)]


# --- Example usage ---
if __name__ == "__main__":
    print("Fetching stock market & financial events from Kalshi...")
    events = fetch_stock_market_financial_events(status="open")
    print(f"Found {len(events)} event(s)\n")
    for ev in events:
        print(f"  - {ev.get('title', 'N/A')}")
        print(f"    Series: {ev.get('series_ticker')} | Event: {ev.get('event_ticker')}")
        for m in ev.get("markets") or []:
            prob = extract_yes_probability(m)
            prob_str = f"{prob:.1%}" if prob is not None else "N/A"
            print(f"    Market: {market_target_label(m)} | YES prob: {prob_str}")
        print()
