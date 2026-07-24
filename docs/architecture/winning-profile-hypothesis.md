# Winning Profile Hypothesis™ Engine — Architecture

**Module:** WPH (pre-award intelligence)
**Status:** Foundational vertical slice — production-grade
**Owner:** Uzima Amka Ventures · CIOS™ platform

---

## 1. What this is

The Winning Profile Hypothesis™ Engine is the **foundational pre-award intelligence
layer** of CIOS. It operationalizes the management discipline **Procurement
Intelligence™** at the earliest, highest-leverage executive decision point:

> *"Should we invest resources pursuing this opportunity, and what would it take to
> become competitive?"*

It is **not** proposal software, a winner-prediction model, or a report generator.
It is an **explainable evidence-fusion architecture** that infers — from the
pre-proposal evidence package — the characteristics an ideal awardee would most
likely need, **before proposal development begins**.

**Positioning guardrails (enforced in code and copy):**

- CIOS does **not** predict winners or claim certainty about award outcomes.
- CIOS does **not** replace government evaluation.
- Every output is a *hypothesis*, traceable to evidence, with explicit confidence,
  assumptions, and unknown factors.

---

## 2. Decision flow

The engine implements the canonical CIOS pre-award workflow end to end:

```
Opportunity Ingestion
  → Procurement Evidence Analysis      (WPHEvidenceDocument)
  → Signal Extraction & Classification (WPHSignal)
  → Winning Profile Hypothesis™        (WPHProfile + WPHProfileAttribute)
  → Contractor Alignment Analysis™     (WPHAlignment.attribute_alignments)
  → Competitive Alignment Ranking™     (WPHAlignment.rank)
  → Capability Gap Analysis™           (WPHAlignment.gaps)
  → Gap Closure Recommendations™       (WPHAlignment.gap_closures)
  → Pursuit Decision Quality (PDQ™)    (WPHAssessment.pdq_score)
  → Executive Bid / No-Bid Decision    (WPHAssessment.recommendation)
```

## 3. Evidence-fusion algorithm (why it is explainable, not a black box)

**Evidence is the source of truth. The LLM is never the source of truth.** The
core scoring is deterministic Python; Claude is used only for optional narrative
enrichment layered on top of already-computed, auditable numbers.

| Stage | Module | Method |
|---|---|---|
| 1. Extract | `wph/extraction.py` | Each document is split into sentences and scanned against a declarative `SIGNAL_LEXICON`. Every match yields a signal that **preserves the verbatim sentence and its source**. Document type sets an evidentiary-value multiplier (Section M, Q&A, Historical awards weigh more). |
| 2. Classify | `wph/taxonomy.py` | 18 `SignalCategory` values (evaluation emphasis, transition risk, security, past-performance emphasis, price sensitivity, …). Deterministic keyword/phrase driven. |
| 3. Infer | `wph/inference.py` | Signals are grouped under the attributes they drive (`ATTRIBUTE_LIBRARY`). Only attributes with supporting signals are emitted. |
| 4. Weight | `wph/inference.py` | `importance_weight` = intrinsic prior × accumulated signal pressure, **normalized so the profile's weights sum to 100** (e.g. "Transition 18/100"). `evidence_confidence` blends mean classification confidence, corroboration volume, and source-document diversity. `required_level` is the proficiency bar a candidate must clear. |
| 5. Align | `wph/alignment.py` | For each attribute, a contractor's capability level is derived from explicit levels, structured fields (clearances, set-asides), or keyword scan. `alignment = min(1, level/required)`; overall = Σ(importance × met), 0–100. |
| 6. Gap | `wph/alignment.py` | Gap severity = f(importance × gap size): critical / major / moderate / minor. |
| 7. Close | `wph/alignment.py` | Category-specific closure playbook → action type, effort, timeline, feasibility, cost band, projected lift. |
| 8. Assess | `wph/pdq.py` | **PDQ™ measures decision quality, not win probability** — high when evidence is strong *and* the target's position is unambiguous (high or low). Recommendation is rule-based on alignment, closable-vs-unclosable critical gaps, and evidence strength. |

Each `WPHProfileAttribute` row carries the CIOS data model exactly: name,
description, importance weight, evidence confidence, supporting evidence, evidence
source references, reasoning, unknown factors, and confidence level.

The whole pipeline runs over pure dataclasses (`wph/schemas.py`) with **no DB or
network dependency**, so it is fully unit-tested (`tests/unit/test_winning_profile_engine.py`).

## 4. Service architecture

The prescribed 11 services map onto CIOS's existing layered architecture (no
duplicated infra — shared auth, RBAC, tenant management, notifications, design
system):

| Prescribed service | Realized as |
|---|---|
| Document Ingestion | `WPHEvidenceDocument` + `POST …/documents` |
| Evidence Extraction | `wph/extraction.py :: SignalExtractor` |
| Signal Classification | `wph/taxonomy.py` (`SIGNAL_LEXICON`) |
| Attribute Inference | `wph/inference.py :: AttributeInferenceEngine` |
| Evidence Weighting | `wph/inference.py` (weighting + confidence math) |
| Winning Profile Hypothesis | `wph/inference.py :: build_profile` + `WPHProfile` |
| Contractor Intelligence | `WPHContractor` + `POST …/contractors` |
| Alignment Scoring | `wph/alignment.py :: AlignmentScorer` / `rank_alignments` |
| Gap Analysis | `wph/alignment.py` (gap derivation) |
| Gap Closure Recommendation | `wph/alignment.py :: GapCloser` |
| Explainability | evidence preserved at every row; `wph/pdq.py` narrative + assumptions; optional `agents/winning_profile_agent.py` |

Orchestration: `wph/engine.py :: WinningProfileEngine` (pure) →
`wph/service.py :: WPHService` (ORM persistence) →
`api/v1/endpoints/winning_profile.py` (REST) and
`tasks/winning_profile.py` (async/bulk).

## 5. Data model

Eight tenant-scoped tables (migration `005_winning_profile_schema`), all with
PostgreSQL **row-level security** on `app.current_tenant`:

- `wph_solicitations` — the evidence package + pipeline status
- `wph_evidence_documents` — Sources Sought, RFI, Draft RFP, SOW/PWS/SOO, Section L/M, Q&A, amendments, historical awards, …
- `wph_signals` — extracted, classified acquisition signals (verbatim evidence + source)
- `wph_profiles` — the versioned Winning Profile Hypothesis™ (`is_current`)
- `wph_profile_attributes` — inferred attributes (full CIOS attribute data model)
- `wph_contractors` — candidate contractor capability profiles (own org / incumbent / competitor)
- `wph_alignments` — per-contractor alignment, ranking, gaps, and closures
- `wph_assessments` — PDQ™ + Executive Opportunity Intelligence Assessment™

## 6. API contract (prefix `/api/v1/winning-profile`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/solicitations` | Create a solicitation package |
| GET | `/solicitations` | List (paginated) |
| GET/DELETE | `/solicitations/{id}` | Fetch / delete |
| POST | `/solicitations/{id}/documents` | Add an evidence document |
| GET | `/solicitations/{id}/documents` | List documents |
| POST | `/solicitations/{id}/extract-signals` | Extract & classify signals |
| GET | `/solicitations/{id}/signals` | List signals (+ counts by category) |
| POST | `/solicitations/{id}/generate-profile` | Generate the Winning Profile Hypothesis™ (`?enrich=true` for Claude narrative) |
| GET | `/solicitations/{id}/profile` | Current hypothesis + attributes |
| POST/GET/DELETE | `/contractors` | Manage contractor capability profiles |
| POST | `/solicitations/{id}/align` | Contractor Alignment + Ranking |
| GET | `/solicitations/{id}/alignments[/{contractor_id}]` | Rankings / one contractor's gaps + closures |
| POST | `/solicitations/{id}/assess` | PDQ™ + bid/no-bid assessment |
| GET | `/solicitations/{id}/assessment` | Latest assessment |
| POST | `/solicitations/{id}/run` | **Full pipeline, synchronous** |
| GET | `/solicitations/{id}/intelligence` | Aggregate: solicitation + profile + rankings + assessment |
| POST | `/sample` | Seed the built-in worked example and run the pipeline |

## 7. Security model

- **Tenant isolation:** every table carries `tenant_id`; all queries filter on it;
  PostgreSQL RLS policies enforce `tenant_id = current_setting('app.current_tenant')`
  as defense in depth.
- **Auth/RBAC:** shared `Auth` dependency (JWT); tenant context set per request.
- **No cross-tenant data:** contractors, profiles, and assessments are strictly
  tenant-owned. No shared vector/graph state across tenants.
- **Auditability:** every recommendation is traceable to the verbatim evidence and
  its source document; assessments always carry explicit assumptions and unknowns.
- **No tenant data in logs** — only IDs.

## 8. Event architecture

- Synchronous path (default): the API runs the deterministic pipeline inline — it
  is fast and needs no queue.
- Async path: `cios.tasks.winning_profile.run_pipeline` (Celery, `analysis` queue)
  for bulk re-runs when new evidence lands, and for off-request-path Claude
  enrichment. Failures set `pipeline_status = failed` and retry with backoff.

## 9. Frontend

`/dashboard/winning-profile` (`WinningProfileView`): create/seed solicitations,
run the intelligence pipeline, and read the Winning Profile Hypothesis™ (weighted
attributes with expandable evidence + reasoning), the Competitive Alignment
Ranking™, and the Executive Assessment (PDQ™, recommendation, critical gaps,
gap-closure actions, assumptions). Gated by the `winning_profile` feature flag
(Professional tier and above).

## 10. Testing & deployment

```bash
# Backend unit tests (pure engine, no DB required)
cd apps/api && pytest tests/unit/test_winning_profile_engine.py -v

# Apply the schema
alembic upgrade head        # includes 005_winning_profile_schema

# One-call end-to-end demo (auth required)
curl -X POST $API/api/v1/winning-profile/sample -H "Authorization: Bearer $JWT"
```

The sample dataset (`cios/wph/sample_data.py`) is a mid-size federal IT
modernization + O&M recompete with a security overlay, an SDVOSB set-aside, and an
active incumbent — exercising transition risk, past-performance emphasis, security
gating, and set-aside eligibility.
