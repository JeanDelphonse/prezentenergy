"""
Industry News Agent — daily-cached EV/battery news + regulatory updates.

Performance strategy:
  - All RSS feeds fetched in parallel (ThreadPoolExecutor)
  - Federal Register fetch runs concurrently with RSS fetching
  - Both Claude curation calls run in parallel
  - Results persisted to instance/news_cache.json (shared across all
    Passenger worker processes)
  - App startup triggers a warm-up fetch in the background so the
    cache is ready before the first user visits
"""

import re
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import anthropic
import requests

# ── File cache path ───────────────────────────────────────────────────────────
_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
_CACHE_FILE = os.path.normpath(
    os.path.join(_BASE_DIR, "..", "instance", "news_cache.json")
)

# ── In-memory cache (per Passenger worker) ───────────────────────────────────
_cache: dict = {"news": None, "regulations": None, "updated": None}
_fetch_lock  = threading.Lock()
_is_fetching = False
CACHE_TTL    = timedelta(hours=24)

# ── RSS sources ───────────────────────────────────────────────────────────────
NEWS_FEEDS = [
    "https://electrek.co/feed/",
    "https://cleantechnica.com/feed/",
    "https://www.greencarreports.com/rss/news",
]


# ── File cache helpers ────────────────────────────────────────────────────────

def _write_file_cache(news: list, regulations: list) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        tmp = _CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "news":        news,
                "regulations": regulations,
                "updated":     datetime.utcnow().isoformat(),
            }, f)
        os.replace(tmp, _CACHE_FILE)
    except Exception:
        pass


def _read_file_cache() -> tuple:
    try:
        with open(_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        updated = datetime.fromisoformat(data["updated"])
        return data["news"], data["regulations"], updated
    except Exception:
        return None, None, None


def _load_file_cache_into_memory() -> bool:
    """Populate in-memory cache from file. Returns True if still valid."""
    news, regs, updated = _read_file_cache()
    if news is None:
        return False
    _cache["news"]        = news
    _cache["regulations"] = regs
    _cache["updated"]     = updated
    return (datetime.utcnow() - updated) < CACHE_TTL


# ── Data fetching (parallelised) ──────────────────────────────────────────────

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_rss(url: str, limit: int = 20) -> list[dict]:
    try:
        r = requests.get(url, timeout=7,
                         headers={"User-Agent": "PrezentEnergy-NewsAgent/1.0"})
        r.raise_for_status()
        root  = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:limit]:
            title    = _strip_html(item.findtext("title", ""))
            link     = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            desc     = _strip_html(item.findtext("description", ""))[:200]
            if title and link:
                items.append({"title": title, "link": link,
                               "date": pub_date, "description": desc})
        return items
    except Exception:
        return []


def _fetch_all_rss() -> list[dict]:
    """Fetch all RSS feeds in parallel."""
    items: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(NEWS_FEEDS)) as ex:
        futures = {ex.submit(_parse_rss, url): url for url in NEWS_FEEDS}
        for fut in as_completed(futures):
            try:
                items.extend(fut.result())
            except Exception:
                pass
    return items


def _fetch_federal_register() -> list[dict]:
    try:
        r = requests.get(
            "https://www.federalregister.gov/api/v1/documents.json",
            params={
                "conditions[term]":   "electric vehicle charging",
                "conditions[type][]": ["RULE", "PROPOSED_RULE", "NOTICE"],
                "per_page":           25,
                "order":              "newest",
            },
            timeout=7,
        )
        r.raise_for_status()
        items = []
        for doc in r.json().get("results", []):
            title    = (doc.get("title") or "").strip()
            url      = doc.get("html_url", "")
            pub_date = doc.get("publication_date", "")
            abstract = _strip_html(doc.get("abstract") or "")[:200]
            if title and url:
                items.append({"title": title, "link": url,
                               "date": pub_date, "description": abstract})
        return items
    except Exception:
        return []


def _curate_with_claude(items: list[dict], section: str, n: int = 10) -> list[dict]:
    fallback = [{"title": i["title"], "date": i["date"], "url": i["link"]}
                for i in items[:n]]
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
            "UL 9741 / UL 1741 / IEEE 1547 bidirectional-charging safety, "
            "ISO 15118-20 V2G communication protocol, "
            "California SB 100 (100% clean energy by 2045), "
            "LCFS 2026, DOE Infrastructure eXCHANGE grants, battery recycling"
        ),
    }

    items_text = "\n".join(
        f"{idx + 1}. TITLE: {item['title']}\n   DATE:  {item['date']}\n   URL:   {item['link']}"
        for idx, item in enumerate(items)
    )
    prompt = (
        f"From these articles, select the {n} most relevant to: {focus_map[section]}\n\n"
        f"{items_text}\n\n"
        f"Return ONLY a JSON array of exactly {n} objects with keys: "
        '"title" (string), "date" (string), "url" (string). '
        "No markdown fences, no explanation — only the JSON array."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp   = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if "```" in text:
            parts = text.split("```")
            text  = parts[1] if len(parts) > 1 else parts[0]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
        return json.loads(text)
    except Exception:
        return fallback


# ── Background fetch (fully parallelised) ─────────────────────────────────────

def _do_fetch() -> None:
    global _is_fetching
    try:
        # Fetch RSS and Federal Register in parallel
        with ThreadPoolExecutor(max_workers=2) as ex:
            rss_future = ex.submit(_fetch_all_rss)
            reg_future = ex.submit(_fetch_federal_register)
            raw_news = rss_future.result()
            raw_regs = reg_future.result()

        # Curate both sections in parallel
        with ThreadPoolExecutor(max_workers=2) as ex:
            news_future = ex.submit(_curate_with_claude, raw_news, "news", 10)
            reg_future  = ex.submit(_curate_with_claude, raw_regs, "regulations", 10)
            news_items  = news_future.result()
            reg_items   = reg_future.result()

        _write_file_cache(news_items, reg_items)
        _cache["news"]        = news_items
        _cache["regulations"] = reg_items
        _cache["updated"]     = datetime.utcnow()
    except Exception:
        pass
    finally:
        _is_fetching = False


# ── Public API ────────────────────────────────────────────────────────────────

def get_industry_news(force_refresh: bool = False) -> tuple:
    """
    Return (news_items, regulation_items) immediately.

    Priority:
      1. In-memory cache (warm, same worker)  → instant
      2. File cache (fresh)                   → instant
      3. Stale / missing → start background thread, return stale/empty
    """
    global _is_fetching
    now = datetime.utcnow()

    # 1. In-memory hit
    if (not force_refresh
            and _cache["updated"] is not None
            and (now - _cache["updated"]) < CACHE_TTL):
        return _cache["news"], _cache["regulations"]

    # 2. File cache
    if not force_refresh and _load_file_cache_into_memory():
        return _cache["news"], _cache["regulations"]

    # 3. Stale / missing — kick off background refresh
    with _fetch_lock:
        if not _is_fetching:
            _is_fetching = True
            threading.Thread(target=_do_fetch, daemon=True).start()

    return _cache["news"] or [], _cache["regulations"] or []


def is_loading() -> bool:
    return _is_fetching


def warm_up() -> None:
    """
    Called at app startup to pre-populate the cache before any user
    visits the page.  Runs in a daemon thread — safe to call from
    create_app().
    """
    news, regs, updated = _read_file_cache()
    if news and updated and (datetime.utcnow() - updated) < CACHE_TTL:
        # File cache is still fresh — load into memory and return
        _load_file_cache_into_memory()
        return
    # Stale or missing — fetch in background
    global _is_fetching
    with _fetch_lock:
        if not _is_fetching:
            _is_fetching = True
            threading.Thread(target=_do_fetch, daemon=True).start()
