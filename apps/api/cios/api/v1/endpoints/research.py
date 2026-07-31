"""Research — Executive Council report access.

Read-only, tenant-facing surface over the platform-owned, non-tenant-scoped
research tables (cios/models/research.py). Gated on Tenant.is_council_member
— a manual admin-set flag (see admin.py's grant/revoke endpoints), not a
self-service subscription feature.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.research import ResearchReport
from cios.models.tenant import Tenant

router = APIRouter()


async def _require_council_membership(db: DB, user: Auth) -> None:
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.is_council_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Executive Council membership required for research access.",
        )


@router.get("/reports", response_model=dict)
async def list_reports(db: DB, user: Auth) -> dict:
    """Council members see every published report, council-only or public.
    Non-members would only ever be entitled to the public ones, but Phase 1
    doesn't yet publish anything as public — enforce full membership for now."""
    await _require_council_membership(db, user)

    rows = (
        (
            await db.execute(
                select(ResearchReport)
                .where(
                    ResearchReport.status == "published",
                    ResearchReport.is_archived == False,  # noqa: E712
                )
                .order_by(ResearchReport.published_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "report_type": r.report_type,
                "period_label": r.period_label,
                "title": r.title,
                "summary": r.summary,
                "published_at": r.published_at.isoformat() if r.published_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/reports/{report_id}", response_model=dict)
async def get_report(report_id: uuid.UUID, db: DB, user: Auth) -> dict:
    await _require_council_membership(db, user)

    report = await db.get(ResearchReport, report_id)
    if not report or report.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return {
        "id": str(report.id),
        "report_type": report.report_type,
        "period_label": report.period_label,
        "title": report.title,
        "summary": report.summary,
        "content": report.content,
        "published_at": report.published_at.isoformat() if report.published_at else None,
    }
