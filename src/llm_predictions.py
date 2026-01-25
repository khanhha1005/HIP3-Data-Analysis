"""
LLM helpers for filtering and summarizing prediction events by symbol.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
import google.generativeai as genai

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

LLM_SYSTEM_PROMPT = (
    "You are an equity prediction analyst. You will be given a target symbol "
    "(ticker) and a list of Polymarket events with markets. Keep ONLY events "
    "that are clearly about the target symbol or its underlying company/ETF "
    "AND are about price, volume, revenue, or general stock outlook/insight. "
    "Exclude unrelated events even if the ticker letters appear in other words. "
    "Exclude sector/index-only events unless the symbol itself is explicitly "
    "referenced. Use event title, description, and market questions to decide. "
    "Return JSON with: {'related_events': [{'slug': str, 'title': str, "
    "'confidence': float, 'reason': str}], 'summary': str}. The summary should "
    "be 1-3 sentences highlighting the most relevant prediction themes and "
    "probabilities."
)

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


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def has_gemini_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def build_event_payload(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    payload = []
    for ev in events:
        payload.append(
            {
                "slug": ev.get("slug"),
                "title": ev.get("title"),
                "description": ev.get("description"),
                "endDate": ev.get("endDate"),
                "markets": [
                    {
                        "question": m.get("question"),
                        "groupItemTitle": m.get("groupItemTitle"),
                        "slug": m.get("slug"),
                        "outcomes": m.get("outcomes"),
                        "outcomePrices": m.get("outcomePrices"),
                    }
                    for m in (ev.get("markets") or [])
                ],
            }
        )
    return payload


def llm_filter_predictions(
    symbol: str,
    events: List[Dict[str, Any]],
    model: Optional[str] = None,
    provider: str = "openai",
) -> Dict[str, Any]:
    if provider == "gemini" and (not has_gemini_key() or not events):
        return {
            "related_events": [],
            "summary": "",
            "model": model or DEFAULT_GEMINI_MODEL,
            "skipped": True,
            "provider": "gemini",
        }
    if provider != "gemini" and (not has_openai_key() or not events):
        return {
            "related_events": [],
            "summary": "",
            "model": model or DEFAULT_MODEL,
            "skipped": True,
            "provider": "openai",
        }

    symbol_aliases = COMPANY_ALIASES.get(symbol, [])

    payload = {
        "symbol": symbol,
        "aliases": symbol_aliases,
        "events": events,
    }

    if provider == "gemini":
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model_name = model or DEFAULT_GEMINI_MODEL
        gemini_model = genai.GenerativeModel(
            model_name,
            system_instruction=LLM_SYSTEM_PROMPT,
        )
        response = gemini_model.generate_content(
            json.dumps(payload),
            generation_config={"temperature": 0.2},
        )
        content = response.text or "{}"
        model_used = model_name
        provider_used = "gemini"
    else:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        model_used = model or DEFAULT_MODEL
        provider_used = "openai"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {}

    related_events = data.get("related_events") or []
    summary = data.get("summary") or ""

    if not isinstance(related_events, list):
        related_events = []
    if not isinstance(summary, str):
        summary = ""

    return {
        "related_events": related_events,
        "summary": summary,
        "model": model_used,
        "skipped": False,
        "provider": provider_used,
    }
