#!/usr/bin/env python3
"""
polymarket_price_predictions.py

Fetch Polymarket (Gamma API) price-prediction markets related to a set of equity tickers
for a given year (default: 2026). Discovers events via /public-search, then pulls full
event payloads via /events/slug/{slug} and extracts implied probabilities from markets.

Outputs:
- out/combined_<year>.csv  (all rows)
- out/<TICKER>/<event_slug>.csv
- out/<TICKER>/<event_slug>.png  (if --plots)

Install:
  pip install requests pandas matplotlib

Example:
  python polymarket_price_predictions.py \
    --year 2026 \
    --tickers AAPL TSLA NVDA META GOOGL AMZN MSFT NFLX \
    --outdir out \
    --plots
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -----------------------------
# Config
# -----------------------------
DEFAULT_BASE_URL = "https://gamma-api.polymarket.com"
DEFAULT_HEADERS = {
    # Mimic a normal browser UA (often avoids 403)
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# -----------------------------
# Helpers
# -----------------------------
def iso_year(dt_str: Optional[str]) -> Optional[int]:
    if not dt_str:
        return None
    try:
        # Gamma API typically uses ISO8601 with Z
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).year
    except Exception:
        return None


def safe_json_list(value: Any) -> List[Any]:
    """
    Gamma fields like outcomes/outcomePrices are sometimes:
      - already a list
      - a JSON string: '["Yes","No"]'
      - a python-ish string: "['Yes','No']"
      - None
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        # try strict JSON first
        try:
            return json.loads(s)
        except Exception:
            # try converting single quotes to double quotes
            try:
                return json.loads(s.replace("'", '"'))
            except Exception:
                return []
    return []


def extract_yes_probability(market: Dict[str, Any]) -> Optional[float]:
    """
    For typical Polymarket binary markets, outcomePrices corresponds to outcomes.
    We return the price for outcome "Yes" if present, else fallback to index 0.
    """
    outcomes = safe_json_list(market.get("outcomes"))
    prices = safe_json_list(market.get("outcomePrices"))

    # Convert prices to floats when possible
    fprices: List[float] = []
    for p in prices:
        try:
            fprices.append(float(p))
        except Exception:
            fprices.append(float("nan"))

    if outcomes and fprices and len(outcomes) == len(fprices):
        # Prefer "Yes" explicitly if present (case-insensitive)
        for i, o in enumerate(outcomes):
            if isinstance(o, str) and o.strip().lower() == "yes":
                return fprices[i] if pd.notna(fprices[i]) else None

    # Fallback: assume index 0 is YES
    if fprices:
        return fprices[0] if pd.notna(fprices[0]) else None

    return None


def market_target_label(market: Dict[str, Any]) -> str:
    # For grouped range markets, groupItemTitle is usually the bucket label
    return (
        market.get("groupItemTitle")
        or market.get("question")
        or market.get("slug")
        or "Unknown"
    )


def sort_key_from_label(label: str) -> float:
    """
    Sort bucket labels by the first number found.
    Handles things like "<$235", "$250-$255", ">$280", "Above $250".
    """
    nums = re.findall(r"\d+(?:\.\d+)?", label.replace(",", ""))
    key = float(nums[0]) if nums else 0.0

    # bias to keep < at start and > at end
    if "<" in label:
        key -= 0.1
    elif ">" in label:
        key += 0.1

    return key


def parse_midpoint(label: str) -> Optional[float]:
    """
    Try to infer a numeric midpoint from common bucket formats:
      - "$250-$255" -> 252.5
      - "<$235" -> 234.5 (heuristic)
      - ">$280" -> 280.5 (heuristic)
    Returns None if it doesn't look like a range bucket.
    """
    s = label.replace(",", "")
    # Range "A-B"
    m = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", s)
    if m:
        a = float(m.group(1))
        b = float(m.group(2))
        return (a + b) / 2.0

    # "<X"
    m = re.search(r"<\s*\$?\s*(\d+(?:\.\d+)?)", s)
    if m:
        x = float(m.group(1))
        return x - 0.5

    # ">X"
    m = re.search(r">\s*\$?\s*(\d+(?:\.\d+)?)", s)
    if m:
        x = float(m.group(1))
        return x + 0.5

    # Pure number bucket "$250"
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*$", s)
    if m and ("Above" not in s and "Below" not in s):
        return float(m.group(1))

    return None


def slugify_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "event"


# -----------------------------
# Gamma API client
# -----------------------------
@dataclass
class GammaClient:
    base_url: str = DEFAULT_BASE_URL
    timeout_s: int = 20
    session: Optional[requests.Session] = None

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(DEFAULT_HEADERS)

            retry = Retry(
                total=5,
                backoff_factor=0.6,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    def public_search_events(
        self,
        q: str,
        page: int = 1,
        limit_per_type: int = 50,
        keep_closed_markets: int = 1,
        events_status: str = "all",
    ) -> Dict[str, Any]:
        """
        GET /public-search?q=...
        """
        url = f"{self.base_url}/public-search"
        params = {
            "q": q,
            "page": page,
            "limit_per_type": limit_per_type,
            "keep_closed_markets": keep_closed_markets,
            "events_status": events_status,
            # You can add: sort, ascending, optimized, recurrence, etc.
        }
        r = self.session.get(url, params=params, timeout=self.timeout_s)
        r.raise_for_status()
        return r.json()

    def get_event_by_slug(self, slug: str) -> Dict[str, Any]:
        """
        GET /events/slug/{slug}
        """
        url = f"{self.base_url}/events/slug/{slug}"
        r = self.session.get(url, timeout=self.timeout_s)
        r.raise_for_status()
        return r.json()


# -----------------------------
# Core logic
# -----------------------------
def discover_event_slugs_for_ticker(
    client: GammaClient,
    ticker: str,
    year: int,
    max_pages: int = 6,
    sleep_s: float = 0.15,
) -> List[Dict[str, Any]]:
    """
    Use multiple queries to increase recall, then filter down to the given year.
    Returns event stubs (from public-search) containing slug/title/endDate.
    """
    queries = [
        f"{ticker} {year}",
        f"{ticker} close {year}",
        f"{ticker} closes {year}",
        f"{ticker} hit {year}",
    ]

    seen: Dict[str, Dict[str, Any]] = {}

    for q in queries:
        for page in range(1, max_pages + 1):
            try:
                payload = client.public_search_events(q=q, page=page)
            except Exception as e:
                print(f"[WARN] public-search failed for q={q!r} page={page}: {e}")
                break

            events = payload.get("events") or []
            for ev in events:
                slug = ev.get("slug")
                if not slug:
                    continue
                seen[slug] = ev

            pagination = payload.get("pagination") or {}
            has_more = bool(pagination.get("hasMore"))
            if not has_more:
                break

            time.sleep(sleep_s)

    # Filter to the requested year using title/slug and/or endDate year
    year_str = str(year)
    out: List[Dict[str, Any]] = []
    for slug, ev in seen.items():
        title = (ev.get("title") or "")
        end_year = iso_year(ev.get("endDate"))
        if (
            year_str in slug
            or year_str in title
            or end_year == year
        ):
            out.append(ev)

    # Deterministic-ish ordering: newest endDate first when possible
    out.sort(key=lambda e: (e.get("endDate") or ""), reverse=True)
    return out


def extract_event_markets_rows(
    ticker: str,
    event: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Convert an event payload (with markets) into flat rows.
    """
    rows: List[Dict[str, Any]] = []

    markets = event.get("markets") or []
    for m in markets:
        label = market_target_label(m)
        yes_p = extract_yes_probability(m)

        rows.append(
            {
                "ticker": ticker,
                "event_id": event.get("id"),
                "event_slug": event.get("slug"),
                "event_title": event.get("title"),
                "event_endDate": event.get("endDate"),
                "event_startDate": event.get("startDate"),
                "market_id": m.get("id"),
                "market_slug": m.get("slug"),
                "target": label,
                "prob_yes": yes_p,
                "sort_key": sort_key_from_label(label),
                # Optional market metadata (present for many markets)
                "volume": m.get("volumeNum") or m.get("volume"),
                "liquidity": m.get("liquidityNum") or m.get("liquidity"),
                "lastTradePrice": m.get("lastTradePrice"),
                "bestBid": m.get("bestBid"),
                "bestAsk": m.get("bestAsk"),
            }
        )

    return rows


def maybe_expected_value(df: pd.DataFrame) -> Optional[float]:
    """
    Try to compute an expected value if the buckets look like non-overlapping ranges.
    Heuristic: most targets have a midpoint, and probabilities sum near 1.
    """
    if df.empty or "prob_yes" not in df:
        return None

    midpoints = df["target"].apply(parse_midpoint)
    ok = midpoints.notna().mean()
    p_sum = df["prob_yes"].fillna(0).sum()

    if ok < 0.7:
        return None
    if not (0.7 <= p_sum <= 1.3):
        return None

    mp = midpoints.fillna(0).astype(float)
    p = df["prob_yes"].fillna(0).astype(float)
    denom = p.sum()
    if denom <= 0:
        return None
    return float((mp * p).sum() / denom)


def plot_event_distribution(df: pd.DataFrame, title: str, outpath: str) -> None:
    import matplotlib.pyplot as plt

    df = df.copy()
    df["prob_yes"] = pd.to_numeric(df["prob_yes"], errors="coerce").fillna(0.0)
    df = df.sort_values("sort_key")

    plt.figure(figsize=(14, 7))
    bars = plt.bar(df["target"], df["prob_yes"], alpha=0.85)

    plt.title(title, fontsize=14, fontweight="bold", pad=16)
    plt.xlabel("Bucket / Target")
    plt.ylabel("Implied Probability (YES price)")
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.3)

    for bar in bars:
        h = bar.get_height()
        if h >= 0.01:
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                h,
                f"{h:.1%}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    plt.tight_layout()
    plt.savefig(outpath, dpi=200)
    plt.close()


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument(
        "--tickers",
        nargs="+",
        default=["AAPL", "TSLA", "NVDA", "META", "GOOGL", "AMZN", "MSFT", "NFLX"],
    )
    ap.add_argument("--outdir", type=str, default="out")
    ap.add_argument("--max-pages", type=int, default=6)
    ap.add_argument("--plots", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--base-url", type=str, default=os.getenv("GAMMA_BASE_URL", DEFAULT_BASE_URL))
    args = ap.parse_args()

    client = GammaClient(base_url=args.base_url)

    os.makedirs(args.outdir, exist_ok=True)
    all_rows: List[Dict[str, Any]] = []

    for ticker in args.tickers:
        print(f"\n=== {ticker} ===")
        ticker_dir = os.path.join(args.outdir, ticker)
        os.makedirs(ticker_dir, exist_ok=True)

        event_stubs = discover_event_slugs_for_ticker(
            client=client,
            ticker=ticker,
            year=args.year,
            max_pages=args.max_pages,
            sleep_s=args.sleep,
        )

        if not event_stubs:
            print(f"[INFO] No {args.year} events found for {ticker}.")
            continue

        # Dedupe by slug
        slugs: List[str] = []
        for ev in event_stubs:
            s = ev.get("slug")
            if s and s not in slugs:
                slugs.append(s)

        print(f"[INFO] Found {len(slugs)} candidate events for {ticker} in/for {args.year}.")

        for slug in slugs:
            try:
                event = client.get_event_by_slug(slug)
            except Exception as e:
                print(f"[WARN] Failed to fetch event slug={slug!r}: {e}")
                continue

            rows = extract_event_markets_rows(ticker=ticker, event=event)
            if not rows:
                continue

            df = pd.DataFrame(rows)
            df["prob_yes"] = pd.to_numeric(df["prob_yes"], errors="coerce")

            # Save per-event CSV
            fname = slugify_filename(event.get("slug") or slug) + ".csv"
            csv_path = os.path.join(ticker_dir, fname)
            df.sort_values("sort_key").to_csv(csv_path, index=False)

            ev_title = event.get("title") or slug
            ev_end = event.get("endDate")
            est = maybe_expected_value(df)

            msg = f"  - {ev_title} (endDate={ev_end}) -> {len(df)} markets"
            if est is not None:
                msg += f" | approx E[price] ≈ {est:.2f}"
            print(msg)

            if args.plots:
                png_path = os.path.join(ticker_dir, slugify_filename(event.get("slug") or slug) + ".png")
                plot_event_distribution(
                    df=df,
                    title=f"{ticker}: {ev_title}",
                    outpath=png_path,
                )

            all_rows.extend(rows)
            time.sleep(args.sleep)

    if all_rows:
        combined = pd.DataFrame(all_rows)
        combined["prob_yes"] = pd.to_numeric(combined["prob_yes"], errors="coerce")
        combined = combined.sort_values(["ticker", "event_endDate", "event_slug", "sort_key"], ascending=[True, False, True, True])
        combined_path = os.path.join(args.outdir, f"combined_{args.year}.csv")
        combined.to_csv(combined_path, index=False)
        print(f"\n[OK] Wrote combined CSV: {combined_path}")
    else:
        print("\n[INFO] No rows collected.")


if __name__ == "__main__":
    main()
