"""007 — Force row-level security on every tenant-scoped table.

Every prior migration did `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and
created a `tenant_isolation` policy, but never `FORCE ROW LEVEL SECURITY`.
Per Postgres semantics, a table's owner bypasses RLS entirely unless RLS is
forced — and the application connects as the same role that owns every table
it created via these migrations (cios_user, both locally and via
docker-compose). That means every tenant_isolation policy has been a no-op
for the app's actual runtime connection: RLS looked enabled, but nothing was
ever actually enforced by it. Application-layer tenant_id filtering is the
only thing that has ever isolated tenants — this migration makes the
database-level backstop real.

Revision ID: 007_force_rls
Revises: 006_wph_shaping_risk
Create Date: 2026-07-21
"""

from __future__ import annotations

from alembic import op

revision = "007_force_rls"
down_revision = "006_wph_shaping_risk"
branch_labels = None
depends_on = None

# Every table with a tenant_isolation RLS policy as of migrations 001-005.
_RLS_TABLES = (
    "opportunities",
    "award_simulations",
    "knowledge_documents",
    "knowledge_chunks",
    "agent_runs",
    "agent_run_steps",
    "capabilities",
    "capability_gaps",
    "past_performances",
    "competitors",
    "competitor_intelligence",
    "bid_decisions",
    "teaming_recommendations",
    "teaming_partners",
    "pir_companies",
    "pir_signals",
    "pir_watchlists",
    "pir_saved_searches",
    "pir_ai_analyses",
    "pir_scan_jobs",
    "wph_solicitations",
    "wph_evidence_documents",
    "wph_signals",
    "wph_profiles",
    "wph_profile_attributes",
    "wph_contractors",
    "wph_alignments",
    "wph_assessments",
)


def upgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
