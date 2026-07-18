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

# Worker
celery -A cios.tasks worker --loglevel=info
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
- **Row-level security** — PostgreSQL RLS on every tenant-scoped table. Enforce via `app.current_tenant` session variable.

## Testing

```bash
cd apps/api
pytest tests/ -v --cov=cios
```

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

## Security Rules

- Never log tenant data (only IDs)
- Never share vector collections across tenants
- All encryption uses tenant-derived keys
- Audit log every data access and mutation
- JWT tokens validated on every request
