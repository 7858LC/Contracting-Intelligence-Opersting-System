# CIOS System Architecture

## Architecture Philosophy

> "Optimize for building the Bloomberg Terminal of procurement — not an AI demo."

Every design decision prioritizes:
1. **Explainability** — every AI output traces to evidence
2. **Trust** — users verify, AI recommends
3. **Auditability** — immutable evidence trail
4. **Security** — zero trust, tenant isolation
5. **Extensibility** — procurement-framework driven, not agency-specific

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                              │
│  Next.js 14 Web App   │   Mobile (Phase 2)   │   API (SDK)     │
└─────────────┬───────────────────────────────────────────────────┘
              │ HTTPS / JWT
┌─────────────▼───────────────────────────────────────────────────┐
│                    CIOS API GATEWAY                              │
│              FastAPI + Uvicorn (async)                           │
│         Rate limiting │ Auth │ Tenant isolation                  │
└──────┬───────────────────────────────────┬────────────────────── ┘
       │                                   │
┌──────▼──────────┐                ┌───────▼──────────┐
│  CIOS REST API  │                │  Celery Workers  │
│  (FastAPI)      │                │  (Async tasks)   │
│  - All 15 mods  │                │  - AI analysis   │
│  - Auth         │                │  - Ingestion     │
│  - Admin        │                │  - Simulation    │
└──────┬──────────┘                └───────┬──────────┘
       │                                   │
┌──────▼───────────────────────────────────▼──────────────────────┐
│                      DATA LAYER                                  │
│  PostgreSQL 16     │    Redis 7      │    Qdrant (Vector)        │
│  (RLS enabled)     │    (Cache+Q)    │    (Per-tenant)           │
│  pgvector          │                 │    (Encrypted)            │
└──────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│                   AI ORCHESTRATION LAYER                          │
│  CEO Agent (claude-opus-4-8)                                      │
│  ├─ Director Agents (claude-sonnet-4-6)                          │
│  │  └─ Analyst Agents (claude-haiku-4-5)                         │
│  └─ Award Simulator (claude-opus-4-8)                            │
└────────────────────────────────────────────────────────────────── ┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│                   EXTERNAL DATA SOURCES                           │
│  SAM.gov API  │  USASpending  │  FPDS-NG  │  State Portals       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Design

### Core Principles
- **Row-Level Security** on every tenant-scoped table
- PostgreSQL `current_setting('app.current_tenant')` pattern
- UUID primary keys (gen_random_uuid())
- JSONB for flexible metadata fields
- TSVECTOR + GIN index for full-text search
- TimestampTZ for all dates (UTC enforced)

### Tables

```
tenants                   -- Core tenant registry
tenant_members            -- User → Tenant membership
tenant_invites            -- Pending invitations
api_keys                  -- Hashed API keys
audit_logs                -- Immutable, append-only

opportunities             -- Module 1 (RLS)
opportunity_watches       -- User watching an opportunity
opportunity_notes         -- Notes on opportunities

bid_decisions             -- Module 2 (RLS)
bid_decision_factors      -- Individual scoring factors

capabilities              -- Module 5 (RLS)
capability_gaps           -- Gap analysis results

past_performances         -- Module 6 (RLS)
past_performance_tags     -- Classification tags

teaming_recommendations   -- Module 7 (RLS)
teaming_partners          -- Partner registry

competitors               -- Module 8 (RLS)
competitor_intelligence   -- Intel records

award_simulations         -- Module 13 (RLS)  ← FLAGSHIP
award_simulation_sections -- Factor-level results

knowledge_documents       -- Knowledge Vault (RLS)
knowledge_chunks          -- Vectorized chunks

agent_runs               -- AI execution audit trail (RLS)
agent_run_steps          -- Step-by-step reasoning trace

subscriptions            -- Billing (no RLS - internal)
invoices                 -- Invoice records
```

---

## Vector Architecture

### Per-Tenant Isolation
```
qdrant/
  collections/
    cios_tenant_{tenant_id_1}/   -- Tenant A's knowledge
    cios_tenant_{tenant_id_2}/   -- Tenant B's knowledge (NEVER mixed)
    ...
```

### Embedding Model
- Primary: Voyage AI (voyage-3) via Anthropic
- Dimension: 1024
- Distance: Cosine similarity
- Per-tenant collection — no cross-contamination

### Search Flow
```
User Query
  → Embed with voyage-3
  → Qdrant vector search (tenant-scoped collection)
  → Filter by document_type, tags
  → Score threshold filter
  → Return top-k chunks with metadata
  → Inject into agent context
```

---

## AI Orchestration Architecture

### Decision Flow
```
User triggers analysis
  → API receives request
  → Celery task queued
  → CEO Agent invoked
  │
  ├─ CaptureDirector.run()
  │   ├─ BidAnalystAgent
  │   ├─ AwardProbabilityAgent
  │   └─ ProposalReadinessAgent
  │
  ├─ ComplianceDirector.run()
  │   ├─ FARComplianceAnalyst
  │   └─ CMMCAnalyst
  │
  ├─ CompetitiveIntelDirector.run()
  ├─ PricingDirector.run()
  ├─ RiskDirector.run()
  │
  └─ CEO.synthesize(all_director_outputs)
      → Structured executive recommendation
      → Stored in DB with audit trail
      → User sees only recommendations
```

### Prompt Architecture
- System prompts are static, version-controlled
- User content injected only in user turn
- Tool use disabled (pure text analysis)
- Temperature = 0.0 for reproducibility
- JSON output parsing with fallback

---

## Security Architecture

### Zero Trust Network
- All services in private VPC subnet
- No public endpoints except API Gateway + ALB
- mTLS between services (Phase 2)
- VPC flow logs enabled

### Authentication Flow
```
Client → HTTPS → ALB → FastAPI
  1. Bearer token extracted
  2. JWT verified (RS256)
  3. tenant_id extracted from payload
  4. SET app.current_tenant = tenant_id (PostgreSQL)
  5. All queries automatically scoped to tenant
```

### Encryption Layers
```
Network: TLS 1.3
Storage: AES-256-GCM (S3 SSE-KMS)
Database: Transparent Data Encryption (RDS)
Field-level: Fernet (PBKDF2-derived per-tenant key)
Vector embeddings: AES-256 at Qdrant storage layer
```

### Customer-Owned Key (Enterprise)
```
Enterprise tenant provides:
  - AWS KMS CMK ARN
  
CIOS derives:
  - Per-tenant Fernet key from CMK
  - Qdrant collection encryption key
  
Result:
  - Customer can revoke access at any time
  - CIOS cannot read data without customer's CMK
```

---

## Event Architecture

### Celery Queues
```
Queue: default        → General tasks
Queue: simulations    → Award Simulator (high memory, long-running)
Queue: ingestion      → Document ingestion + vectorization
Queue: analysis       → Opportunity analysis
Queue: email          → Email delivery
```

### Future: Event Bus (Phase 2)
```
NATS JetStream or AWS EventBridge
  → Opportunity change events
  → Analysis complete events
  → Subscription change events
  → Webhook delivery
```

---

## Observability

### Logging (Structured JSON)
```json
{
  "timestamp": "2026-07-18T12:00:00Z",
  "level": "info",
  "event": "simulation_complete",
  "agent": "award_simulator_agent",
  "tenant_id": "...",
  "duration_ms": 45231,
  "model": "claude-opus-4-8",
  "tokens_used": 8192
}
```

### Metrics (Prometheus)
- `cios_api_requests_total` — request count by endpoint
- `cios_api_latency_seconds` — latency histogram
- `cios_agent_runs_total` — AI agent invocations
- `cios_agent_duration_seconds` — agent execution time
- `cios_simulation_duration_seconds` — simulation duration
- `cios_ai_tokens_total` — token usage by model

### Traces (OpenTelemetry)
- Distributed traces through API → Celery → AI layers
- Correlation IDs on every request
- Agent run IDs linked to traces
