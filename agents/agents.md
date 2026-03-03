# Agents — Developer & AI-Agent Reference

This file is the authoritative guide for any agent (human or AI) maintaining
code in `agents/` and keeping `docs/` synchronized with the implementation.

---

## Directory map

| File | Purpose | Primary doc it implements |
|---|---|---|
| `chatbot.py` | Claude-powered sales assistant | `docs/prd.txt` §3 (Chatbot) |
| `news_agent.py` | Conversational news/regulatory Q&A | `docs/prd.txt` §3 (News Agent) |
| `industry_news_agent.py` | Daily-cached RSS + Federal Register feed | `docs/industry_news_prd.txt` |

---

## Agent summaries

### chatbot.py
- Loads `static/about/prezent_energy_fact_base.txt` at import time as its sole
  knowledge source.
- Calls `claude-sonnet-4-6`, `max_tokens=1024`.
- Entry point: `get_chat_response(messages: list[dict]) -> str`
- Route: `POST /api/chat` (defined in `routes/chat.py`)

### news_agent.py
- Stateless conversational agent; no cache.
- Calls `claude-sonnet-4-6`, `max_tokens=1500`.
- Maintains optional `conversation_history` for multi-turn sessions.
- Entry point: `query_news_agent(user_query, conversation_history) -> str`
- Route: `POST /api/news-query`

### industry_news_agent.py
- Two-layer cache: in-memory (per worker) → file (`instance/news_cache.json`).
- Cache TTL: 24 hours; background thread refreshes stale data without blocking.
- RSS sources: Electrek, CleanTechnica, Green Car Reports.
- Regulatory source: Federal Register API (rules / proposed rules / notices).
- Claude Haiku (`claude-haiku-4-5-20251001`) curates raw items down to top 10
  per category (news, regulations).
- Public API: `get_industry_news(force_refresh=False) -> (news_items, reg_items)`
- Status check: `is_loading() -> bool` (polled by JS frontend)
- Route: `GET /api/industry-news`

---

## Doc-to-code mapping

Use this table to know **which doc to update when code changes**.

| What changed in code | Doc(s) to update |
|---|---|
| Chatbot system prompt / fact base path | `docs/prd.txt` §3 Chatbot section |
| Chatbot model or token limit | `docs/prd.txt` §3; `CLAUDE.md` AI Chatbot section |
| `news_agent.py` focus areas or system prompt | `docs/prd.txt` §3 News Agent section |
| `industry_news_agent.py` RSS feeds | `docs/industry_news_prd.txt` §1 Section 1 sources |
| `industry_news_agent.py` regulatory API or filters | `docs/industry_news_prd.txt` §1 Section 2 focus areas |
| Cache TTL or cache strategy | `docs/industry_news_prd.txt` implementation notes |
| Lead form fields (`models.py`) | `docs/prd.txt` §4; `CLAUDE.md` Lead model section |
| New route added | `docs/prd.txt` §3 or §4; `CLAUDE.md` Architecture section |
| New agent file added | This file (add row to directory map + agent summary) |
| Login / auth behaviour | `docs/login_prd.txt`; `docs/login_EV_User_Onboarding.txt` |
| Business numbers (pricing, stats) | `docs/prd.txt` §2 F and §6; `CLAUDE.md` Key Business Numbers |

---

## Rules for keeping docs current

1. **Code is the source of truth for behaviour; docs are the source of truth
   for intent.**  When they diverge, update the doc to match the code *unless*
   the code is wrong — in that case fix the code first, then verify the doc.

2. **Minimal, targeted edits.**  Only update the exact sections that changed.
   Do not rewrite unrelated paragraphs.

3. **Preserve the original tone.**  `docs/prd.txt` uses business/marketing
   language; `CLAUDE.md` uses technical shorthand.  Match the existing style.

4. **Quote numbers precisely.**  Business figures (`$633M`, `$800–$1,200`,
   `90–130 hours`, etc.) appear in both code system prompts and docs.  Any
   change to a figure must be propagated to every location listed in the table
   above.

5. **After adding a new agent:**
   - Add a row to the directory map table.
   - Write an agent summary section.
   - Add a row (or rows) to the doc-to-code mapping table.
   - Register the route in `CLAUDE.md` Architecture if applicable.

6. **After removing an agent:**
   - Delete its row from the directory map and its summary section.
   - Remove or archive the corresponding PRD section if the feature is gone.
   - Remove the route from `CLAUDE.md`.

7. **Chatbot fact base.**  `static/about/prezent_energy_fact_base.txt` is
   loaded at runtime, not hardcoded in `chatbot.py`.  When specs change,
   update the fact base file directly; also update `docs/prd.txt` §3 to
   describe the new capabilities.

---

## Checklist — before committing an agent change

- [ ] Does the agent summary above still accurately describe the file?
- [ ] Are model IDs and token limits reflected in the relevant PRD?
- [ ] Have all business numbers that appear in system prompts been verified
      against `docs/prd.txt` §6 and `CLAUDE.md` Key Business Numbers?
- [ ] If a new external API or RSS feed was added, is it listed in the PRD?
- [ ] Did the cache strategy change? If so, is `industry_news_prd.txt` updated?
- [ ] Does `CLAUDE.md` still accurately describe the routes and architecture?
