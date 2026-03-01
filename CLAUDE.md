# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Build the **Prezent.Energy** marketing and lead-generation website as specified in `docs/prd.txt`. The site targets three B2B segments: City Vehicle Fleets, Business Campuses, and Residential Complexes.

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend | Flask (Python) | Consistent with sibling projects in this workspace |
| Database | SQLite via SQLAlchemy | Required by PRD; portable and maintenance-friendly |
| Frontend | Jinja2 templates + Tailwind CSS | No build step needed for MVP |
| AI Chatbot | Anthropic Claude API | Trained on PRD specs and V2X roadmap |
| News Agent | Anthropic Claude API + web search | Dynamic CaaS/regulatory feed |

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py          # starts Flask on port 5000

# Initialize/migrate the database
flask db init
flask db migrate -m "initial"
flask db upgrade
# or for simple bootstrap without migrations:
python -c "from app import db; db.create_all()"

# Run tests
pytest tests/

# Run a single test
pytest tests/test_leads.py::test_submit_lead -v
```

## Architecture

### Directory layout (target)

```
prezentenergy/
├── app.py               # Flask app factory and route registration
├── models.py            # SQLAlchemy models (Lead)
├── config.py            # Environment-based config (dev/prod)
├── docs/
│   └── prd.txt          # Product requirements document
├── requirements.txt
├── .env                 # API keys, DB path (never commit)
├── static/
│   ├── css/             # Tailwind output or custom CSS
│   ├── js/              # Chat widget, form validation, scroll effects
│   └── video/           # Embedded robot demo video asset
├── templates/
│   ├── base.html        # Layout, nav, footer (contact info in footer)
│   ├── index.html       # Single-page sections A–G (see PRD §2)
│   └── partials/        # Hero, pricing, team, FAQ, CTA form partials
├── agents/
│   ├── chatbot.py       # Persistent chatbot — uses Claude API, system prompt from PRD specs
│   └── news_agent.py    # AI news feed agent (DOE, PG&E, LCFS, V2X sources)
├── routes/
│   ├── main.py          # Page routes
│   ├── leads.py         # POST /api/leads — saves to SQLite
│   └── chat.py          # POST /api/chat and POST /api/news-query
└── tests/
```

### Database — Lead model (models.py)

Required fields per PRD §4 and the form spec:

```python
# Primary Contact
full_name, email, phone

# Organization
company_name, industry_segment  # dropdown: City Fleet / Business Campus / Residential / Hotel

# Operational
fleet_size, location_zip, current_charging_status  # Zero / Fixed Insufficient / Planning

# Strategic
primary_interests  # comma-separated: Productivity / VPP / CaaS / Carbon

# Intent
timeline, comments

# Metadata
created_at  # timestamp
```

### AI Chatbot (agents/chatbot.py)

- Persistent UI widget on every page (bottom-right corner).
- System prompt must embed: VoltBot specs, pricing tiers, CCS1/CCS2 compatibility, thermal management FAQ, V2X roadmap, 130-hour productivity stat, 800–1,200 VPP earnings figure.
- Endpoint: `POST /api/chat` — streams Claude response back to the widget.

### News Agent (agents/news_agent.py)

- Replaces a static blog. Users type a query; agent fetches relevant context.
- Source categories to monitor/query: DOE Infrastructure eXCHANGE (GDO/MESC), PG&E PAC updates, Portable DC Fast Charger market data, CA SB 100, LCFS 2026, ISO 15118-20 / UL 9741.
- Endpoint: `POST /api/news-query` — returns summarized, cited results.

### Page Sections (index.html)

Build as one long-scroll page with anchor IDs matching the PRD section letters:

| ID | Section | Key content |
|---|---|---|
| `#hero` | Hero | Embedded video (src: www.prezent.energy), headline, 3 value callouts |
| `#challenge` | Workplace Challenge | Old Way vs New Way comparison ($50K+, 6–12 mo vs $0, 1 week) |
| `#caas` | CaaS | Infrastructure-Lite advantages |
| `#how-it-works` | 4-Step Journey | BOOK → CHARGE → REPORT → GRID SUPPORT |
| `#integration` | Seamless Integration | Equipment + liability handled |
| `#pricing` | Pricing | Starter / Corporate / Enterprise table |
| `#team` | Management Team | 4 bios (Cameron, Andersen, Delphonse, Novak) |
| `#faq` | FAQ | Thermal mgmt, CCS1/CCS2, dongle-to-direct transition |
| `#demo` | CTA / Schedule Demo | Full lead-capture form → POST /api/leads |

### Environment Variables (.env)

```
ANTHROPIC_API_KEY=
FLASK_ENV=development
DATABASE_URL=sqlite:///leads.db
SECRET_KEY=
```

## Key Business Numbers (embed in copy and chatbot system prompt)

- `$0` infrastructure investment, `1-week` launch, `100% employee coverage`
- Old way: `$50,000+` per station, `6–12 month` install
- `90–130 hours` annual employee time saved
- `36%` of Americans in multi-unit housing lack charging access
- VPP earnings: `$800–$1,200/year` per vehicle
- Portable DC Fast Charger market: `$633M by 2033`

## Contact (Footer)

```
www.prezent.energy | (408) 758-8293 | info@prezent.energy
```
