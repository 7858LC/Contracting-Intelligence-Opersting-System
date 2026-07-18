# UzimaAmka Platform — Architecture Overview

*For the full technical implementation, see the `/apps` directory.*

## Platform Philosophy

The UzimaAmka platform is built on four architectural principles:

### 1. Evidence-First AI
Every AI recommendation surfaces its evidence, confidence score, regulatory citation, key assumptions, and alternatives considered. No black-box outputs. Capture professionals make better decisions when they understand why the system recommends what it recommends.

### 2. Per-Tenant Data Isolation
Every customer's data — including vector embeddings, knowledge vault contents, and competitive intelligence — is completely isolated. Zero cross-contamination between tenants. This is non-negotiable in a market where data confidentiality is a trust prerequisite.

### 3. Procurement-Framework Driven
The platform is built around universal procurement concepts with jurisdiction-specific rule packs. It is not a U.S.-federal-only tool. FAR, DFARS, EU procurement directives, World Bank guidelines, and state/local frameworks are all supported through the rule pack architecture.

### 4. Intelligence as Infrastructure
The platform is not a reporting tool. It is an intelligence substrate — a layer that sits beneath capture decisions and continuously improves as more data flows through it.

## Core System Components

### Intelligence Ingestion Layer
- Automated ingestion from SAM.gov, USASpending.gov, and configured data sources
- Document processing pipeline: PDF, DOCX, XLSX, plain text
- Structured intelligence extraction using Claude Opus AI
- Per-tenant knowledge vault with Qdrant vector store

### AI Orchestration Layer
- **CEO Agent** (Claude Opus 4.8): Strategic synthesis, bid/no-bid recommendations, award simulation
- **Director Agents** (Claude Sonnet): Opportunity analysis, competitive intelligence, teaming strategy
- **Analyst Agents** (Claude Haiku): Data extraction, pattern recognition, report generation
- Hierarchical orchestration: users see only recommendations, never agent internals

### Analysis Engine
- Bid/No-Bid scoring across 8 Shipley-derived dimensions
- Award probability modeling with confidence intervals
- Source selection simulation (FAR 15.305 / DFARS implementation)
- Competitive positioning and counter-strategy generation
- Past performance relevance scoring

### Security Layer
- Zero Trust architecture: every request authenticated and authorized
- Row-Level Security: PostgreSQL RLS with per-request tenant context
- Per-tenant encryption: PBKDF2 Fernet keys, customer-owned KMS option for Enterprise
- Immutable audit log: every data access and AI recommendation logged

## Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.12), async/await throughout |
| Database | PostgreSQL 16 with RLS, SQLAlchemy async |
| Vector Store | Qdrant (per-tenant collections) |
| Embeddings | Voyage AI (voyage-3, 1024-dim) |
| AI Models | Anthropic Claude (Opus/Sonnet/Haiku) |
| Task Queue | Celery + Redis |
| Frontend | Next.js 14, TypeScript, TanStack Query |
| Infrastructure | AWS (ECS Fargate, RDS, ElastiCache, S3) |
| Billing | Stripe |
