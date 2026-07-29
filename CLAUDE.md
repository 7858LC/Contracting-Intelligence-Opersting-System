# CIOS — Contract Intelligence Operating System

## What This Is

A production-grade SaaS procurement intelligence platform. The Bloomberg Terminal of procurement. NOT proposal software, NOT CRM, NOT document management.

## Project Structure

```
apps/
  api/          FastAPI backend (Python 3.12)
  web/          Next.js 14 frontend (TypeScript)
infra/
  docker/       Docker Compose for local dev
  kubernetes/   K8s manifests
  terraform/    AWS infrastructure
docs/
  prd/          Product Requirements Document
  architecture/ Architecture documents
```

## Running Locally

```bash
# Start dependencies
npm run docker:up

# Backend
cd apps/api && pip install -e ".[dev]"
uvicorn cios.main:app --reload --port 8000

# Frontend
cd apps/web && npm install && npm run dev

# Worker — the -Q list must match every queue in cios/tasks/__init__.py's
# task_routes plus any task's own queue= override (grep the tasks/ package
# for `queue=` if you add a new one); omitting a queue here means Celery
# silently never runs the tasks routed to it — this exact gap went
# undetected for a long time because "celery" (Celery's real default queue)
# had been misnamed "default" here, which doesn't exist.
#
# CIOS_WORKER_PROCESS=1 is required on any process running task bodies —
# it switches core/database.py to NullPool, since every task calls
# asyncio.run() (a fresh event loop per task) and a real connection pool
# would hand out a connection bound to a previous, already-closed loop.
# Never set this on the API process (uvicorn) — it keeps one long-lived
# loop and should keep real pooling.
CIOS_WORKER_PROCESS=1 celery -A cios.tasks worker --loglevel=info -Q celery,simulations,ingestion,analysis,email,pir_scan,research

# Scheduler (required for the daily PIR scan and quarterly research brief
# to actually fire — a worker alone does not run scheduled tasks)
CIOS_WORKER_PROCESS=1 celery -A cios.tasks beat --loglevel=info
```

## Environment

Copy `.env.example` to `.env` and populate. Required:
- `ANTHROPIC_API_KEY` — Claude API key
- `DATABASE_URL` — PostgreSQL async connection string
- `JWT_SECRET` — minimum 32 characters
- `ENCRYPTION_KEY` — 64 hex characters (32 bytes)

## Key Architecture Decisions

- **Procurement-framework driven** — not government-specific. Universal procurement concepts with jurisdiction-specific rule packs.
- **Evidence-first AI** — every recommendation includes confidence score, evidence, regulatory citation, assumptions, and alternatives. Never surface AI outputs without this structure.
- **Per-tenant vector isolation** — each tenant gets a private Qdrant collection. Zero cross-contamination.
- **Hierarchical agent orchestration** — CEO Agent → Directors → Analysts. Users see only recommendations, never agent internals.
- **Row-level security** — PostgreSQL RLS on every tenant-scoped table. Enforce via `app.current_tenant` session variable, set once in `get_current_user`/`get_current_platform_admin` (`core/dependencies.py`) directly on the request's cached DB session — safe to declare `db`/`user` in any order in a route signature. A background task or script outside that dependency chain (Celery tasks, `scripts/*.py`) must set it itself before any RLS-scoped query, e.g. `SELECT set_config('app.current_tenant', :tenant_id, false)`; nothing sets it for you.
- **Commercial SaaS, not a federal system of record** — CIOS serves government contractors, not government agencies. It derives decision intelligence from public procurement data and customer-owned inputs only; it never stores or processes CUI, classified information, or export-controlled technical data. Customer strategy belongs to the customer, government data stays with the government.
- **Landlord/tenant separation** — platform operators (`PlatformAdmin`) are a distinct identity space from tenant users, never tenant-scoped and never RLS-subject. Landlord JWTs carry a `scope: platform_admin` claim that tenant tokens never have (and vice versa for `tenant_id`), so the two audiences are never interchangeable. No self-service signup for landlord accounts — provision via `apps/api/scripts/create_platform_admin.py`. Landlord API lives under `/api/v1/admin`, console UI under `apps/web/src/app/admin`; every tenant-ops action (suspend/activate) writes an `AuditLog` row attributed to the acting admin.

## Testing Discipline

This project runs on the Damascus Protocol — schema drift, wiring bugs, and cross-module breakage get caught automatically as the codebase evolves, instead of accumulating silently until one big pre-launch sweep finds them all at once (which is exactly what happened here once: a dependency-order bug, a response-type mismatch, and 14 drifted tables all shipped clean through review and sat live until the first real end-to-end test pass hit them). Four mechanisms carry that going forward: the `alembic check` CI gate below, the module checklist's step 8, the shared fixtures in `tests/integration/conftest.py`, and a weekly automated regression sweep against a real Postgres + Redis. None of these are ceremony. Don't skip or bypass one because a change feels too small to bother — that exact reasoning is how each of the three bugs above shipped in the first place.

```bash
cd apps/api
pytest tests/ -v --cov=cios
```

`tests/integration/` requires a real, migrated Postgres + Redis — `docker compose -f infra/docker/docker-compose.yml up postgres redis` locally, same setup CI uses. These can't run against a mock; that's the point (see `tests/integration/conftest.py`). Two things that bite new integration tests:
- Anything hitting `/auth/register` or `/auth/login` needs a distinct `X-Forwarded-For` header per call, or the shared-IP test harness trips the endpoint's own rate limiter (`core/rate_limit.py`).
- After changing a model, run `alembic check` (also gates CI) before writing a migration by hand — it tells you exactly what's out of sync instead of finding out from a 500 later.

**Production migrations are automated** — `render.yaml`'s `cios-api` service runs `alembic upgrade head` as a `preDeployCommand` on every deploy, before the new release takes traffic. Never run `alembic upgrade head` against production by hand anymore; it happens automatically, and a failing migration now aborts the deploy (keeping the previous release live) instead of shipping code against an unmigrated schema. This replaced the prior manual-only workflow, which is exactly the kind of step that gets forgotten under time pressure.

## AI Models

- CEO Agent: `claude-opus-4-8`
- Director Agents: `claude-sonnet-4-6`
- Analyst Agents: `claude-haiku-4-5-20251001`
- Award Simulator: `claude-opus-4-8`

## Adding a New Module

1. Create model in `apps/api/cios/models/`
2. Add Alembic migration in `apps/api/alembic/versions/`
3. Create API endpoints in `apps/api/cios/api/v1/endpoints/`
4. Register router in `apps/api/cios/api/v1/router.py`
5. Create agent in `apps/api/cios/agents/`
6. Create Celery task in `apps/api/cios/tasks/`
7. Add frontend page in `apps/web/src/app/dashboard/`
8. Add at least one smoke test in `apps/api/tests/integration/` exercising the new endpoint(s) through the real HTTP/DB/Redis stack (see `test_module_smoke.py`) — this is the tier that catches wiring bugs (broken imports, missing router registration, model/migration drift) that unit tests and manual testing both miss.

## Security Rules

- Never log tenant data (only IDs)
- Never share vector collections across tenants
- All encryption uses tenant-derived keys
- Audit log every data access and mutation
- JWT tokens validated on every request
