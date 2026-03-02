"""
Industry News Agent — daily-cached EV/battery news + regulatory updates.

Fetches real articles from RSS feeds and the Federal Register API,
then uses Claude Haiku to curate the top 5 most relevant items for each section.
Results are cached in memory for 24 hours (no database storage per PRD §2).
"""

import re
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import anthropic
import requests

# ── Module-level cache ────────────────────────────────────────────────────────
_cache: dict = {"news": None, "regulations": None, "updated": None}
CACHE_TTL = timedelta(hours=24)

# ── RSS sources (EV / battery focus) ─────────────────────────────────────────
NEWS_FEEDS = [
    "https://electrek.co/feed/",
    "https://cleantechnica.com/feed/",
    "https://www.greencarreports.com/rss/news",
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_rss(url: str, limit: int = 20) -> list[dict]:
    """Fetch an RSS feed and return a list of article dicts."""
    try:
        r = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "PrezentEnergy-NewsAgent/1.0"},
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = _strip_html(item.findtext("title", ""))
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            desc = _strip_html(item.findtext("description", ""))[:200]
            if title and link:
                items.append(
                    {"title": title, "link": link, "date": pub_date, "description": desc}
                )
        return items
    except Exception:
        return []


def _fetch_federal_register() -> list[dict]:
    """Query the Federal Register API for recent EV-related rules/notices."""
    try:
        r = requests.get(
            "https://www.federalregister.gov/api/v1/documents.json",
            params={
                "conditions[term]": "electric vehicle charging",
                "conditions[type][]": ["RULE", "PROPOSED_RULE", "NOTICE"],
                "per_page": 25,
                "order": "newest",
            },
            timeout=10,
        )
        r.raise_for_status()
        items = []
        for doc in r.json().get("results", []):
            title = (doc.get("title") or "").strip()
            url = doc.get("html_url", "")
            pub_date = doc.get("publication_date", "")
            abstract = _strip_html(doc.get("abstract") or "")[:200]
            if title and url:
                items.append(
                    {"title": title, "link": url, "date": pub_date, "description": abstract}
                )
        return items
    except Exception:
        return []


def _curate_with_claude(items: list[dict], section: str, n: int = 5) -> list[dict]:
    """
    Ask Claude Haiku to pick the top-N most relevant articles and return
    a JSON array of {title, date, url} objects.
    Falls back to the first N raw items if the API call fails.
    """
    fallback = [
        {"title": i["title"], "date": i["date"], "url": i["link"]}
        for i in items[:n]
    ]
    if not items:
        return fallback

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return fallback

    focus_map = {
        "news": (
            "portable DC fast charger market growth ($633M by 2033), "
            "autonomous mobile charging robots (VoltBot, Gotion Gen2-EPLVS), "
            "V2X / V2G / V2L / V2V emerging trends, "
            "LiFePO4 and sodium-ion battery breakthroughs, "
            "EV charging infrastructure expansion"
        ),
        "regulations": (
            "UL 9741 / UL 1741 / IEEE 1547 bidirectional-charging safety standards, "
            "ISO 15118-20 V2G communication protocol, "
            "California SB 100 (100% clean energy by 2045), "
            "LCFS 2026 implementation, "
            "DOE Infrastructure eXCHANGE grants, "
            "battery recycling policy"
        ),
    }

    items_text = "\n".join(
        f"{idx + 1}. TITLE: {item['title']}\n   DATE:  {item['date']}\n   URL:   {item['link']}"
        for idx, item in enumerate(items)
    )

    prompt = (
        f"From these articles, select the {n} most relevant to: {focus_map[section]}\n\n"
        f"{items_text}\n\n"
        f"Return ONLY a JSON array of exactly {n} objects. "
        "Each object must have these keys: "
        '"title" (string), "date" (string), "url" (string). '
        "No markdown fences, no explanation — only the JSON array."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Strip markdown code fences if model added them
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else parts[0]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
        return json.loads(text)
    except Exception:
        return fallback


def get_industry_news(force_refresh: bool = False) -> tuple[list[dict], list[dict]]:
    """
    Return (news_items, regulation_items).
    Each item: {"title": str, "date": str, "url": str}.
    Results are cached in memory for 24 hours.
    """
    now = datetime.utcnow()
    cache_valid = (
        not force_refresh
        and _cache["updated"] is not None
        and (now - _cache["updated"]) < CACHE_TTL
    )
    if cache_valid:
        return _cache["news"], _cache["regulations"]

    # ── fetch raw data ────────────────────────────────────────────────────────
    raw_news: list[dict] = []
    for feed_url in NEWS_FEEDS:
        raw_news.extend(_parse_rss(feed_url))

    raw_regs = _fetch_federal_register()

    # ── curate with Claude ────────────────────────────────────────────────────
    news_items = _curate_with_claude(raw_news, "news", 10)
    reg_items = _curate_with_claude(raw_regs, "regulations", 10)

    # ── store in cache ────────────────────────────────────────────────────────
    _cache["news"] = news_items
    _cache["regulations"] = reg_items
    _cache["updated"] = now

    return news_items, reg_items
