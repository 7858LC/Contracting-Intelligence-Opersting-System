# CIOS / UzimaAmka — Session Transition Prompt

Use this document verbatim as the opening message of a new session.

---

## Project Identity

**Product name:** UzimaAmka (brand) / CIOS — Contract Intelligence Operating System (internal)
**Tagline:** "The Bloomberg Terminal of Procurement"
**What it is:** Production-grade SaaS procurement intelligence platform for government contractors. NOT proposal software, NOT CRM, NOT document management. The job is intelligence — bid decisions, competitive analysis, award simulation, knowledge management.
**Website:** uzimaAmka.com
**GitHub repo:** `7858lc/contracting-intelligence-opersting-system`
**Working branch:** `claude/cios-platform-architecture-df7978`

---

## Repository Structure

```
apps/
  api/          FastAPI backend (Python 3.12, async SQLAlchemy, Celery)
  web/          Next.js 14 App Router frontend (TypeScript)
infra/
  docker/       Docker Compose for local dev
  kubernetes/   K8s manifests
  terraform/    AWS infrastructure
docs/
  prd/          Product Requirements Documents
  architecture/ Architecture docs
Procurement-Intelligence/   Knowledge base — 20 markdown files across 6 dirs
```

---

## Git State (as of handoff)

Branch is clean and pushed. Last 6 commits:
```
6bde1fc chore: ignore tsconfig.tsbuildinfo build cache
7418804 feat: Knowledge Vault UI overhaul and search result fix
bdafcb0 docs: add Procurement-Intelligence knowledge base structure (20 files)
f4cc807 feat: UzimaAmka rebrand and UI polish pass
72ad07a chore: add GitHub repository URL to package metadata
26b0e37 fix: add tsconfig paths alias and remove non-existent radix badge package
1a58fb0 feat: wire Voyage AI embeddings and add dashboard auth guard
fd82fb5 feat: complete frontend module pages, backend model/endpoint fixes
d2d715d feat: initial CIOS platform architecture — complete production-grade scaffold
```

---

## What Is Fully Built

### Backend (`apps/api/`)

**Framework:** FastAPI, async SQLAlchemy, Alembic, Celery + Redis, Qdrant

**Models (all complete with migrations):**
- `Tenant`, `TenantMember` — multi-tenant foundation with RLS
- `KnowledgeDocument`, `KnowledgeChunk` — Knowledge Vault
- `Opportunity` — Module 1
- `BidDecision` — Module 2
- `AwardSimulation`, `SimulationFactor`, `SimulationResult` — Module 13 (flagship)
- `Capability`, `CapabilityGap` — Module 5
- `PastPerformance` — Module 6
- `TeamingPartner`, `TeamingRecommendation` — Module 7
- `Competitor`, `CompetitorIntel` — Module 8
- `AgentRun` — logs all AI decisions with evidence trail
- `Subscription`, `Invoice` — billing

**API endpoints (all registered in router):**
- `/api/v1/auth` — register, login, refresh, me
- `/api/v1/opportunities` — CRUD + `/analyze` + `/watch`
- `/api/v1/bid-decisions` — CRUD + `/human-decision`
- `/api/v1/award-simulations` — CRUD + `/report`
- `/api/v1/knowledge-vault` — list, upload (multipart), search (semantic), delete
- `/api/v1/capabilities` — CRUD + `/gaps`
- `/api/v1/past-performance` — CRUD
- `/api/v1/teaming` — partners CRUD + `/recommendations` + `/recommend`
- `/api/v1/competitors` — CRUD + `/intel`
- `/api/v1/tenants` — profile, api-keys
- `/api/v1/subscriptions` — current, checkout, portal, invoices
- `/api/v1/agent-runs` — read-only log
- `/api/v1/admin` — internal use

**Agents (structured, evidence-first):**
- `ceo_agent.py` — orchestrates directors, uses `claude-opus-4-8`
- `directors/capture_director.py` — `claude-sonnet-4-6`
- `directors/competitive_intel_director.py`
- `directors/compliance_director.py`
- `directors/pricing_director.py`
- `directors/risk_director.py`
- `award_simulator_agent.py` — `claude-opus-4-8`, FAR 15.305 simulation

**Vector store (`cios/vector/tenant_store.py`):**
- Per-tenant Qdrant collection: `cios_tenant_{uuid}`
- Embeddings: Voyage AI `voyage-3`, 1024 dimensions
- `_embed()` uses `voyageai.AsyncClient`
- `search()` returns `{chunk_id, document_id, document_title, text, score, metadata}`

**Celery tasks:**
- `ingestion.py` — `ingest_document`: extract text (pypdf/docx), chunk (512 words, 64 overlap), embed via Voyage AI, upsert to Qdrant, create `KnowledgeChunk` rows, update doc status
- `ingestion.py` — `vectorize_past_performance`: stub, needs implementation
- `analysis.py`, `bid_analysis.py`, `scoring.py`, `simulation.py`, `competitive_intel.py`, `teaming.py`, `gap_analysis.py`, `onboarding.py`, `billing.py`, `email.py` — all exist, some are stubs

**Config (`cios/config.py`):** All settings via env vars with Pydantic. Required at runtime: `DATABASE_URL`, `JWT_SECRET`, `ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`. Optional but needed for full function: `VOYAGE_API_KEY`, `QDRANT_URL`, `REDIS_URL`.

### Frontend (`apps/web/`)

**Framework:** Next.js 14 App Router, TypeScript, TailwindCSS, shadcn design tokens, Tanstack Query, Axios, Sonner toasts

**Brand palette (globals.css):**
- Primary: `hsl(162 72% 36%)` light / `hsl(162 72% 46%)` dark (teal-green)
- Background dark: `hsl(222 42% 5%)`
- Accent: `hsl(38 95% 50%)` (amber)
- Card dark: `hsl(222 38% 8%)`

**Pages built:**
- `/` → redirects to `/marketing`
- `/marketing` — full landing page with hero, stats, modules grid, Award Simulator section, security section, pricing tiers, footer. Brand: UzimaAmka.
- `/auth/layout.tsx` — split-screen: dark left panel (grid pattern, ambient glow, brand copy, testimonial, stats) + clean right form panel
- `/auth/login` — email/password form, JWT save, redirect to dashboard
- `/auth/register` — company registration form
- `/dashboard` — executive dashboard (top opportunities + recent simulations)
- `/dashboard/opportunities` — opportunity list with status badges, create button
- `/dashboard/bid-decisions` — bid decision list with Go/No-Go/Conditional badges
- `/dashboard/award-simulator` — simulation list + create simulation flow
- `/dashboard/knowledge-vault` — upload (drag-and-drop), doc list with type chips + tags, semantic search with relevance bars
- `/dashboard/capabilities` — capability list + gap analysis
- `/dashboard/teaming` — partner list + AI recommendations
- `/dashboard/competitors` — competitor profiles + intel entries
- `/dashboard/settings` — tenant profile + API keys + billing

**Layout (`dashboard-layout.tsx`):**
- Sidebar with nav items, FLAGSHIP badge on Award Simulator
- JWT auth guard: `useEffect` checks `getAccessToken()`, redirects to `/auth/login` if missing
- Logo: UzimaAmka + "Intelligence Platform" subtitle
- Security indicator: "Encrypted · Zero Trust"

**API client (`lib/api.ts`):** `CIOSApiClient` class with auto-refresh on 401, typed methods for all endpoints. Base URL from `NEXT_PUBLIC_API_URL` env var (default `http://localhost:8000`).

**Known working:** TypeScript compiles clean (`npx tsc --noEmit` exits 0). `typedRoutes` experimental flag is OFF (was causing TS errors without a prior build).

### Knowledge Base (`Procurement-Intelligence/`)

20 markdown files pushed to GitHub:
```
00_Vision/          Category_Definition, Founding_Thesis, Council_Manifesto
01_Research/        Market_Landscape, Government_Buying_Trends, Source_Citations, Competitive_Analysis
02_State_of_.../    Executive_Summary, Chapter_01–06 (Landscape through Founding Council)
03_Frameworks/      PIMM self-assessment, Bid_No_Bid, Award_Simulation_Model, Capture_Intelligence_Model
04_GTM/             LinkedIn_Series, Council_Recruitment, Outreach_Strategy
05_CIOS_Product/    Architecture, Agent_Model, Security_Model
```

---

## Architectural Principles (non-negotiable, do not drift from these)

1. **Evidence-first AI** — every AI output must include: `confidence_score`, `evidence[]`, `rule_citations[]`, `assumptions[]`, `risks[]`, `alternatives[]`. Never surface a recommendation without this structure.
2. **Per-tenant vector isolation** — each tenant gets their own Qdrant collection. Zero cross-contamination. Collection name: `cios_tenant_{uuid_underscored}`.
3. **Hierarchical agent orchestration** — CEO Agent (`claude-opus-4-8`) → Director Agents (`claude-sonnet-4-6`) → Analyst Agents (`claude-haiku-4-5-20251001`). Users see recommendations only, never agent internals.
4. **Procurement-framework driven** — universal concepts + jurisdiction-specific rule packs (FAR, DFARS, EU, World Bank). Not government-only.
5. **Row-level security** — PostgreSQL RLS on every tenant-scoped table via `app.current_tenant` session variable.
6. **Immutable audit trail** — every AI decision logged in `agent_runs` with model version, evidence, and human decision outcome.

---

## What Is NOT Done (Remaining Tasks)

### Priority 1 — Award Simulator (flagship feature, build this first)

The `award_simulator_agent.py` exists but the actual Claude call needs to be wired into the simulation task (`apps/api/cios/tasks/simulation.py`). The agent should:
- Accept opportunity details + proposal content sections
- Run FAR 15.305 / DFARS source selection evaluation
- Return DOD color/adjectival ratings per factor (Outstanding/Good/Acceptable/Marginal/Unacceptable)
- Identify weaknesses, significant weaknesses, deficiencies with red-team commentary
- Output award probability % with confidence score
- Rank improvement actions by expected score impact

The frontend `award-simulator-view.tsx` has the UI shell — it needs the simulation to actually trigger the agent and poll for results.

### Priority 2 — UI Polish Pass

The user explicitly said "this doesn't look like something I'd pay for or use" and "we can come back to this." The marketing page and auth pages have been rebranded to UzimaAmka, but the **dashboard module pages** (opportunities, bid-decisions, capabilities, teaming, competitors, settings) need a visual upgrade. They render functional but sparse UI. Goals:
- More visual hierarchy, better use of color
- Data visualizations where appropriate (e.g., win rate trend, bid decision breakdown)
- Empty states that guide the user rather than just saying "No items"
- The Award Simulator page in particular should feel premium (it's the flagship)

When taking screenshots to show the user, start the dev server: `cd apps/web && npm run dev` and use Playwright + Chromium at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` to capture screenshots (this is a remote cloud container, localhost is not accessible to the user's browser).

### Priority 3 — Backend Wiring (make the app actually run)

The backend has never been started in this project's sessions. To run it:
```bash
cd apps/api
pip install -e ".[dev]"
uvicorn cios.main:app --reload --port 8000
```
Requires: `.env` file with `DATABASE_URL` (PostgreSQL async), `JWT_SECRET`, `ENCRYPTION_KEY` (64 hex chars), `ANTHROPIC_API_KEY`.

Missing wiring:
- `vectorize_past_performance` task in `ingestion.py` is a stub — needs full implementation mirroring `ingest_document`
- Several Celery tasks (`bid_analysis.py`, `scoring.py`, etc.) are stubs — implement as needed when building out module functionality
- Alembic migrations need to be run: `alembic upgrade head`

### Priority 4 — SAM.gov / Opportunity Ingestion (Module 1)

There is no live data pipeline yet. The Opportunity model and endpoints exist, but opportunities are created manually. The real value is automated ingestion from:
- SAM.gov API (key in config: `sam_gov_api_key`)
- USASpending.gov API (key in config: `usaspending_api_key`)

A Celery beat task should poll SAM.gov daily, extract opportunities matching the tenant's NAICS codes, and create `Opportunity` records with AI-extracted intelligence.

### Priority 5 — Stripe Billing Integration

The `Subscription` model, Stripe config vars, and `/api/v1/subscriptions` endpoints are scaffolded. Actual Stripe checkout + webhook handling in `webhooks.py` and `billing.py` needs implementation. Pricing tiers (from marketing page):
- Starter: $499/mo
- Professional: $1,499/mo  
- Enterprise: custom/year

---

## Environment Variables Required

```bash
# Minimum to run backend
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cios
JWT_SECRET=<32+ char random string>
ENCRYPTION_KEY=<64 hex chars (32 bytes)>
ANTHROPIC_API_KEY=<key>

# For vector search (Knowledge Vault)
VOYAGE_API_KEY=<key>
QDRANT_URL=http://localhost:6333   # default

# For production features
REDIS_URL=redis://localhost:6379/0
STRIPE_SECRET_KEY=<key>
SENDGRID_API_KEY=<key>
SAM_GOV_API_KEY=<key>
```

---

## How to Run Locally

```bash
# Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d

# Backend
cd apps/api
pip install -e ".[dev]"
alembic upgrade head
uvicorn cios.main:app --reload --port 8000

# Frontend
cd apps/web
npm install
npm run dev

# Worker
cd apps/api
celery -A cios.tasks worker --loglevel=info
```

---

## Key File Locations

| What | Path |
|------|------|
| Brand CSS tokens | `apps/web/src/styles/globals.css` |
| API client | `apps/web/src/lib/api.ts` |
| Dashboard layout + auth guard | `apps/web/src/components/layout/dashboard-layout.tsx` |
| Award Simulator UI | `apps/web/src/components/modules/simulation/award-simulator-view.tsx` |
| Award Simulator agent | `apps/api/cios/agents/award_simulator_agent.py` |
| Simulation Celery task | `apps/api/cios/tasks/simulation.py` |
| Vector store | `apps/api/cios/vector/tenant_store.py` |
| Document ingestion task | `apps/api/cios/tasks/ingestion.py` |
| All API endpoints | `apps/api/cios/api/v1/endpoints/` |
| All SQLAlchemy models | `apps/api/cios/models/` |
| App config + env vars | `apps/api/cios/config.py` |

---

## Tooling Notes for This Environment

- This is a **remote cloud container**. Localhost is not accessible to the user's browser. To show UI, start the dev server then use **Python Playwright** with the pre-installed Chromium at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`. Capture screenshots and send via `SendUserFile`.
- The GitHub MCP tool (`mcp__github__push_files`) can push files directly to the remote without a local git commit — useful for large file batches. For code changes, use standard git.
- Always run `git pull origin claude/cios-platform-architecture-df7978 --rebase` before pushing if GitHub MCP was used to push files directly (the two histories can diverge).
- TypeScript check: `cd apps/web && npx tsc --noEmit`

---

*Start the next session by reading `CLAUDE.md` (project instructions) and this file. Then ask what to work on, or proceed directly to Priority 1 (Award Simulator) if no specific direction is given.*
