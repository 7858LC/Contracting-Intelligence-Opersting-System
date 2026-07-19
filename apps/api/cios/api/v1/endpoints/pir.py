"""Procurement Intelligence Radar™ (PIR) — REST API endpoints."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from cios.core.dependencies import Auth, DB, Pages
from cios.models.pir import (
    PIRAIAnalysis,
    PIRCompany,
    PIRSavedSearch,
    PIRScanJob,
    PIRSignal,
    PIRWatchlist,
    PriorityTier,
    SignalSource,
    SignalType,
)

router = APIRouter()


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    domain: str | None = Field(None, max_length=256)
    website: str | None = None
    linkedin_url: str | None = None
    samgov_uei: str | None = Field(None, max_length=12)
    cage_code: str | None = Field(None, max_length=10)
    industry: str | None = None
    employee_count_range: str | None = None
    revenue_range: str | None = None
    headquarters_city: str | None = None
    headquarters_state: str | None = None
    naics_codes: list[str] = []
    set_aside_types: list[str] = []
    description: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    industry: str | None = None
    employee_count_range: str | None = None
    revenue_range: str | None = None
    headquarters_city: str | None = None
    headquarters_state: str | None = None
    naics_codes: list[str] | None = None
    set_aside_types: list[str] | None = None
    description: str | None = None
    is_watched: bool | None = None
    is_active: bool | None = None


class CompanyResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    domain: str | None
    website: str | None
    linkedin_url: str | None
    samgov_uei: str | None
    cage_code: str | None
    industry: str | None
    employee_count_range: str | None
    revenue_range: str | None
    headquarters_city: str | None
    headquarters_state: str | None
    headquarters_country: str
    naics_codes: list
    set_aside_types: list
    description: str | None
    overall_signal_score: float
    confidence_score: float
    growth_momentum_score: float
    government_readiness_score: float
    priority_tier: str
    is_active: bool
    is_watched: bool
    last_scanned_at: datetime | None
    last_scored_at: datetime | None
    created_at: datetime
    updated_at: datetime
    signal_count: int = 0

    class Config:
        from_attributes = True


class SignalResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    signal_type: str
    source: str
    source_url: str | None
    title: str
    description: str | None
    raw_weight: float
    decay_factor: float
    effective_weight: float
    detected_at: datetime
    is_verified: bool
    is_duplicate: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    is_default: bool = False


class WatchlistResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_default: bool
    company_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    filters: dict[str, Any] = {}
    notify_on_new: bool = False


class SavedSearchResponse(BaseModel):
    id: uuid.UUID
    name: str
    filters: dict
    last_run_at: datetime | None
    result_count: int
    notify_on_new: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScanJobResponse(BaseModel):
    id: uuid.UUID
    scan_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    companies_discovered: int
    signals_detected: int
    errors: int
    results_summary: dict
    created_at: datetime

    class Config:
        from_attributes = True


class AIAnalysisResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    status: str
    executive_summary: str | None
    pain_points: list
    recommended_outreach: str | None
    buying_probability: float | None
    suggested_messaging: list
    potential_stakeholders: list
    confidence_explanation: str | None
    model_used: str | None
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_companies: int
    tier_a_count: int
    tier_b_count: int
    tier_c_count: int
    watched_count: int
    signals_last_7d: int
    avg_signal_score: float
    top_signal_types: list[dict]
    scan_jobs_running: int


# ── Companies ─────────────────────────────────────────────────────────────────

@router.get("/companies", response_model=dict)
async def list_companies(
    user: Auth,
    db: DB,
    pages: Pages,
    tier: PriorityTier | None = Query(None),
    min_score: float | None = Query(None, ge=0, le=100),
    is_watched: bool | None = Query(None),
    naics_code: str | None = Query(None),
    state: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("overall_signal_score"),
    order: str = Query("desc"),
) -> dict:
    q = select(PIRCompany).where(
        PIRCompany.tenant_id == user.tenant_id,
        PIRCompany.is_active.is_(True),
    )

    if tier:
        q = q.where(PIRCompany.priority_tier == tier)
    if min_score is not None:
        q = q.where(PIRCompany.overall_signal_score >= min_score)
    if is_watched is not None:
        q = q.where(PIRCompany.is_watched.is_(is_watched))
    if state:
        q = q.where(PIRCompany.headquarters_state == state.upper())
    if search:
        q = q.where(PIRCompany.name.ilike(f"%{search}%"))
    if naics_code:
        q = q.where(PIRCompany.naics_codes.contains([naics_code]))

    sort_col = getattr(PIRCompany, sort_by, PIRCompany.overall_signal_score)
    q = q.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    companies = (await db.execute(q.offset(pages.offset).limit(pages.limit))).scalars().all()

    items = []
    for c in companies:
        d = CompanyResponse.model_validate(c).model_dump()
        sig_count = await db.execute(
            select(func.count(PIRSignal.id)).where(PIRSignal.company_id == c.id)
        )
        d["signal_count"] = sig_count.scalar_one()
        items.append(d)

    return {
        "items": items,
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
    }


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, user: Auth, db: DB) -> PIRCompany:
    existing = None
    if payload.domain:
        res = await db.execute(
            select(PIRCompany).where(
                PIRCompany.tenant_id == user.tenant_id,
                PIRCompany.domain == payload.domain,
            )
        )
        existing = res.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company with domain '{payload.domain}' already exists",
        )

    company = PIRCompany(
        tenant_id=user.tenant_id,
        **payload.model_dump(),
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: uuid.UUID, user: Auth, db: DB) -> PIRCompany:
    company = await _get_company_or_404(db, company_id, user.tenant_id)
    return company


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID, payload: CompanyUpdate, user: Auth, db: DB
) -> PIRCompany:
    company = await _get_company_or_404(db, company_id, user.tenant_id)
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(company, field, val)
    await db.commit()
    await db.refresh(company)
    return company


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: uuid.UUID, user: Auth, db: DB) -> None:
    company = await _get_company_or_404(db, company_id, user.tenant_id)
    company.is_active = False
    await db.commit()


@router.post("/companies/{company_id}/scan", status_code=status.HTTP_202_ACCEPTED)
async def trigger_company_scan(
    company_id: uuid.UUID,
    user: Auth,
    db: DB,
    days_back: int = Query(60, ge=1, le=365),
) -> dict:
    company = await _get_company_or_404(db, company_id, user.tenant_id)

    job = PIRScanJob(
        tenant_id=user.tenant_id,
        scan_type="single_company",
        status="pending",
        scan_config={"company_id": str(company_id), "days_back": days_back},
        triggered_by=user.user_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from cios.tasks.pir import scan_company
    scan_company.delay(str(company_id), str(user.tenant_id), {"days_back": days_back})

    return {"job_id": str(job.id), "status": "queued"}


# ── Signals ───────────────────────────────────────────────────────────────────

@router.get("/companies/{company_id}/signals", response_model=dict)
async def list_company_signals(
    company_id: uuid.UUID,
    user: Auth,
    db: DB,
    pages: Pages,
    signal_type: str | None = Query(None),
    source: str | None = Query(None),
    since_days: int | None = Query(None, ge=1, le=365),
    include_duplicates: bool = Query(False),
) -> dict:
    await _get_company_or_404(db, company_id, user.tenant_id)

    q = select(PIRSignal).where(
        PIRSignal.company_id == company_id,
        PIRSignal.tenant_id == user.tenant_id,
    )

    if not include_duplicates:
        q = q.where(PIRSignal.is_duplicate.is_(False))
    if signal_type:
        q = q.where(PIRSignal.signal_type == signal_type)
    if source:
        q = q.where(PIRSignal.source == source)
    if since_days:
        from datetime import timedelta
        cutoff = datetime.now(UTC) - timedelta(days=since_days)
        q = q.where(PIRSignal.detected_at >= cutoff)

    q = q.order_by(PIRSignal.detected_at.desc())

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()
    signals = (await db.execute(q.offset(pages.offset).limit(pages.limit))).scalars().all()

    return {
        "items": [SignalResponse.model_validate(s).model_dump() for s in signals],
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
    }


# ── AI Analysis ───────────────────────────────────────────────────────────────

@router.post(
    "/companies/{company_id}/analyze",
    response_model=AIAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ai_analysis(company_id: uuid.UUID, user: Auth, db: DB) -> PIRAIAnalysis:
    company = await _get_company_or_404(db, company_id, user.tenant_id)

    analysis = PIRAIAnalysis(
        tenant_id=user.tenant_id,
        company_id=company_id,
        status="pending",
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    from cios.tasks.pir import analyze_company_ai
    analyze_company_ai.delay(
        str(company_id),
        str(user.tenant_id),
        str(analysis.id),
        str(user.user_id),
    )

    return analysis


@router.get("/companies/{company_id}/analyses", response_model=dict)
async def list_ai_analyses(
    company_id: uuid.UUID, user: Auth, db: DB, pages: Pages
) -> dict:
    await _get_company_or_404(db, company_id, user.tenant_id)

    q = (
        select(PIRAIAnalysis)
        .where(PIRAIAnalysis.company_id == company_id, PIRAIAnalysis.tenant_id == user.tenant_id)
        .order_by(PIRAIAnalysis.created_at.desc())
    )

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()
    rows = (await db.execute(q.offset(pages.offset).limit(pages.limit))).scalars().all()

    return {
        "items": [AIAnalysisResponse.model_validate(r).model_dump() for r in rows],
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
    }


@router.get("/companies/{company_id}/analyses/{analysis_id}", response_model=AIAnalysisResponse)
async def get_ai_analysis(
    company_id: uuid.UUID, analysis_id: uuid.UUID, user: Auth, db: DB
) -> PIRAIAnalysis:
    row = await db.execute(
        select(PIRAIAnalysis).where(
            PIRAIAnalysis.id == analysis_id,
            PIRAIAnalysis.company_id == company_id,
            PIRAIAnalysis.tenant_id == user.tenant_id,
        )
    )
    analysis = row.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


# ── Watchlists ────────────────────────────────────────────────────────────────

@router.get("/watchlists", response_model=list[WatchlistResponse])
async def list_watchlists(user: Auth, db: DB) -> list[PIRWatchlist]:
    result = await db.execute(
        select(PIRWatchlist)
        .where(PIRWatchlist.tenant_id == user.tenant_id)
        .order_by(PIRWatchlist.is_default.desc(), PIRWatchlist.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/watchlists", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(payload: WatchlistCreate, user: Auth, db: DB) -> PIRWatchlist:
    watchlist = PIRWatchlist(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        **payload.model_dump(),
    )
    db.add(watchlist)
    await db.commit()
    await db.refresh(watchlist)
    return watchlist


@router.delete("/watchlists/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(watchlist_id: uuid.UUID, user: Auth, db: DB) -> None:
    wl = await _get_watchlist_or_404(db, watchlist_id, user.tenant_id)
    await db.delete(wl)
    await db.commit()


@router.post("/watchlists/{watchlist_id}/companies/{company_id}", status_code=status.HTTP_200_OK)
async def add_to_watchlist(
    watchlist_id: uuid.UUID, company_id: uuid.UUID, user: Auth, db: DB
) -> dict:
    wl = await _get_watchlist_or_404(db, watchlist_id, user.tenant_id)
    await _get_company_or_404(db, company_id, user.tenant_id)

    ids: list = list(wl.company_ids or [])
    cid_str = str(company_id)
    if cid_str not in ids:
        ids.append(cid_str)
        wl.company_ids = ids
        wl.company_count = len(ids)
    await db.commit()
    return {"company_count": wl.company_count}


@router.delete("/watchlists/{watchlist_id}/companies/{company_id}", status_code=status.HTTP_200_OK)
async def remove_from_watchlist(
    watchlist_id: uuid.UUID, company_id: uuid.UUID, user: Auth, db: DB
) -> dict:
    wl = await _get_watchlist_or_404(db, watchlist_id, user.tenant_id)
    ids: list = [c for c in (wl.company_ids or []) if c != str(company_id)]
    wl.company_ids = ids
    wl.company_count = len(ids)
    await db.commit()
    return {"company_count": wl.company_count}


# ── Saved Searches ────────────────────────────────────────────────────────────

@router.get("/saved-searches", response_model=list[SavedSearchResponse])
async def list_saved_searches(user: Auth, db: DB) -> list[PIRSavedSearch]:
    result = await db.execute(
        select(PIRSavedSearch)
        .where(PIRSavedSearch.tenant_id == user.tenant_id)
        .order_by(PIRSavedSearch.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/saved-searches", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED
)
async def create_saved_search(payload: SavedSearchCreate, user: Auth, db: DB) -> PIRSavedSearch:
    search = PIRSavedSearch(
        tenant_id=user.tenant_id,
        created_by=user.user_id,
        **payload.model_dump(),
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)
    return search


@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(search_id: uuid.UUID, user: Auth, db: DB) -> None:
    res = await db.execute(
        select(PIRSavedSearch).where(
            PIRSavedSearch.id == search_id,
            PIRSavedSearch.tenant_id == user.tenant_id,
        )
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Saved search not found")
    await db.delete(obj)
    await db.commit()


# ── Scan Jobs ─────────────────────────────────────────────────────────────────

@router.post("/scans", response_model=ScanJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_bulk_scan(
    user: Auth,
    db: DB,
    days_back: int = Query(60, ge=1, le=365),
    watched_only: bool = Query(False),
) -> PIRScanJob:
    job = PIRScanJob(
        tenant_id=user.tenant_id,
        scan_type="bulk_radar_scan",
        status="pending",
        scan_config={"days_back": days_back, "watched_only": watched_only},
        triggered_by=user.user_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from cios.tasks.pir import bulk_radar_scan
    bulk_radar_scan.delay(str(user.tenant_id), None, {"days_back": days_back})

    return job


@router.get("/scans", response_model=dict)
async def list_scan_jobs(user: Auth, db: DB, pages: Pages) -> dict:
    q = (
        select(PIRScanJob)
        .where(PIRScanJob.tenant_id == user.tenant_id)
        .order_by(PIRScanJob.created_at.desc())
    )
    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()
    rows = (await db.execute(q.offset(pages.offset).limit(pages.limit))).scalars().all()
    return {
        "items": [ScanJobResponse.model_validate(r).model_dump() for r in rows],
        "total": total,
        "page": pages.page,
        "page_size": pages.page_size,
    }


@router.get("/scans/{job_id}", response_model=ScanJobResponse)
async def get_scan_job(job_id: uuid.UUID, user: Auth, db: DB) -> PIRScanJob:
    res = await db.execute(
        select(PIRScanJob).where(
            PIRScanJob.id == job_id,
            PIRScanJob.tenant_id == user.tenant_id,
        )
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return job


# ── Dashboard stats ───────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(user: Auth, db: DB) -> DashboardStats:
    from datetime import timedelta
    from sqlalchemy import case, cast, Float

    tid = user.tenant_id

    # Company counts by tier
    tier_counts = await db.execute(
        select(
            PIRCompany.priority_tier,
            func.count(PIRCompany.id),
        ).where(
            PIRCompany.tenant_id == tid,
            PIRCompany.is_active.is_(True),
        ).group_by(PIRCompany.priority_tier)
    )
    tier_map: dict[str, int] = {}
    total_companies = 0
    for tier, cnt in tier_counts.fetchall():
        tier_map[tier] = cnt
        total_companies += cnt

    watched = await db.execute(
        select(func.count(PIRCompany.id)).where(
            PIRCompany.tenant_id == tid,
            PIRCompany.is_watched.is_(True),
            PIRCompany.is_active.is_(True),
        )
    )

    avg_score = await db.execute(
        select(func.avg(PIRCompany.overall_signal_score)).where(
            PIRCompany.tenant_id == tid,
            PIRCompany.is_active.is_(True),
        )
    )

    cutoff = datetime.now(UTC) - timedelta(days=7)
    signals_7d = await db.execute(
        select(func.count(PIRSignal.id)).where(
            PIRSignal.tenant_id == tid,
            PIRSignal.detected_at >= cutoff,
        )
    )

    top_types = await db.execute(
        select(PIRSignal.signal_type, func.count(PIRSignal.id).label("cnt"))
        .where(PIRSignal.tenant_id == tid)
        .group_by(PIRSignal.signal_type)
        .order_by(func.count(PIRSignal.id).desc())
        .limit(5)
    )

    running_scans = await db.execute(
        select(func.count(PIRScanJob.id)).where(
            PIRScanJob.tenant_id == tid,
            PIRScanJob.status.in_(["pending", "running"]),
        )
    )

    return DashboardStats(
        total_companies=total_companies,
        tier_a_count=tier_map.get("A", 0),
        tier_b_count=tier_map.get("B", 0),
        tier_c_count=tier_map.get("C", 0),
        watched_count=watched.scalar_one(),
        signals_last_7d=signals_7d.scalar_one(),
        avg_signal_score=round(avg_score.scalar_one() or 0.0, 1),
        top_signal_types=[
            {"signal_type": st, "count": cnt}
            for st, cnt in top_types.fetchall()
        ],
        scan_jobs_running=running_scans.scalar_one(),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_company_or_404(db: Any, company_id: uuid.UUID, tenant_id: uuid.UUID) -> PIRCompany:
    result = await db.execute(
        select(PIRCompany).where(
            PIRCompany.id == company_id,
            PIRCompany.tenant_id == tenant_id,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


async def _get_watchlist_or_404(
    db: Any, watchlist_id: uuid.UUID, tenant_id: uuid.UUID
) -> PIRWatchlist:
    result = await db.execute(
        select(PIRWatchlist).where(
            PIRWatchlist.id == watchlist_id,
            PIRWatchlist.tenant_id == tenant_id,
        )
    )
    wl = result.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return wl
