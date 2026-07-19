"""PIR Celery tasks — scanning, scoring, and AI analysis."""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from celery import shared_task
from sqlalchemy import select, update

from cios.tasks import celery_app

log = structlog.get_logger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(coro: Any) -> Any:
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


async def _get_db():
    from cios.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        return session


# ── Scan tasks ─────────────────────────────────────────────────────────────────

@celery_app.task(
    name="cios.tasks.pir.scan_company",
    queue="pir_scan",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def scan_company(self, company_id: str, tenant_id: str, scan_config: dict | None = None) -> dict:
    """Scan a single company across all signal sources and upsert signals."""
    try:
        return _run(_async_scan_company(
            uuid.UUID(company_id),
            uuid.UUID(tenant_id),
            scan_config or {},
        ))
    except Exception as exc:
        log.error("scan_company_failed", company_id=company_id, error=str(exc))
        raise self.retry(exc=exc)


async def _async_scan_company(
    company_id: uuid.UUID,
    tenant_id: uuid.UUID,
    scan_config: dict,
) -> dict:
    from cios.core.database import AsyncSessionLocal
    from cios.models.pir import PIRCompany, PIRSignal
    from cios.scanners import JobBoardScanner, SAMGovScanner, USASpendingScanner
    from cios.scoring import SignalScorer

    async with AsyncSessionLocal() as db:
        company = await db.get(PIRCompany, company_id)
        if not company:
            return {"error": f"Company {company_id} not found"}

        keywords = _build_keywords(company)
        naics = list(company.naics_codes or [])
        signals_created = 0
        errors: list[str] = []

        # Run all scanners
        scanners = [
            SAMGovScanner(),
            USASpendingScanner(),
            JobBoardScanner(),
        ]

        for scanner in scanners:
            async with scanner:
                try:
                    result = await scanner.scan(
                        keywords=keywords,
                        naics_codes=naics,
                        days_back=scan_config.get("days_back", 60),
                    )
                    for scanned in result.signals:
                        sig = _upsert_signal(db, company_id, tenant_id, scanned)
                        db.add(sig)
                        signals_created += 1
                    errors.extend(result.errors)
                except Exception as e:
                    errors.append(f"{scanner.source_name}: {e}")
                    log.warning("scanner_error", scanner=scanner.source_name, error=str(e))

        # Update company scan timestamp
        company.last_scanned_at = datetime.now(UTC)
        await db.commit()

        # Trigger re-scoring
        score_company.delay(str(company_id), str(tenant_id))

        return {
            "company_id": str(company_id),
            "signals_created": signals_created,
            "errors": errors,
        }


def _build_keywords(company: Any) -> list[str]:
    """Generate search keywords from company profile."""
    keywords = [company.name]
    if company.domain:
        # Strip TLD for cleaner search
        base = company.domain.split(".")[0]
        if base and base != company.name.lower().replace(" ", ""):
            keywords.append(base)
    if company.naics_codes:
        # Common GovCon NAICS keyword map
        naics_keywords = {
            "541511": "custom software development",
            "541512": "IT consulting",
            "541519": "IT services",
            "541330": "engineering services",
            "541990": "professional services",
            "561210": "facilities management",
            "611420": "training",
        }
        for code in company.naics_codes[:3]:
            kw = naics_keywords.get(str(code))
            if kw:
                keywords.append(kw)
    return keywords[:5]


def _upsert_signal(db: Any, company_id: uuid.UUID, tenant_id: uuid.UUID, scanned: Any) -> Any:
    """Convert a ScannedSignal to a PIRSignal ORM object."""
    from cios.models.pir import PIRSignal
    from cios.scoring import SIGNAL_WEIGHTS

    raw_weight = float(SIGNAL_WEIGHTS.get(scanned.signal_type, 3))
    return PIRSignal(
        company_id=company_id,
        tenant_id=tenant_id,
        signal_type=scanned.signal_type,
        source=scanned.source,
        source_url=scanned.source_url,
        title=scanned.title,
        description=scanned.description,
        raw_weight=raw_weight,
        decay_factor=1.0,
        effective_weight=raw_weight,
        detected_at=scanned.detected_at,
        raw_data=scanned.raw_data,
        is_verified=False,
        is_duplicate=False,
    )


@celery_app.task(
    name="cios.tasks.pir.bulk_radar_scan",
    queue="pir_scan",
    bind=True,
)
def bulk_radar_scan(
    self,
    tenant_id: str,
    company_ids: list[str] | None = None,
    scan_config: dict | None = None,
) -> dict:
    """Fan out individual scan tasks for all (or specified) companies in a tenant."""
    return _run(_async_bulk_scan(tenant_id, company_ids, scan_config or {}))


async def _async_bulk_scan(
    tenant_id: str,
    company_ids: list[str] | None,
    scan_config: dict,
) -> dict:
    from cios.core.database import AsyncSessionLocal
    from cios.models.pir import PIRCompany

    tid = uuid.UUID(tenant_id)
    async with AsyncSessionLocal() as db:
        if company_ids:
            cids = [uuid.UUID(c) for c in company_ids]
            rows = await db.execute(
                select(PIRCompany.id).where(
                    PIRCompany.tenant_id == tid,
                    PIRCompany.id.in_(cids),
                    PIRCompany.is_active.is_(True),
                )
            )
        else:
            rows = await db.execute(
                select(PIRCompany.id).where(
                    PIRCompany.tenant_id == tid,
                    PIRCompany.is_active.is_(True),
                )
            )
        ids = [str(r[0]) for r in rows.fetchall()]

    for cid in ids:
        scan_company.delay(cid, tenant_id, scan_config)

    return {"queued": len(ids), "tenant_id": tenant_id}


# ── Scoring tasks ──────────────────────────────────────────────────────────────

@celery_app.task(
    name="cios.tasks.pir.score_company",
    queue="pir_scan",
    bind=True,
    max_retries=2,
)
def score_company(self, company_id: str, tenant_id: str) -> dict:
    """Recompute all scores for a company and persist to DB."""
    try:
        return _run(_async_score_company(uuid.UUID(company_id), uuid.UUID(tenant_id)))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _async_score_company(company_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
    from cios.core.database import AsyncSessionLocal
    from cios.models.pir import PIRCompany, PIRSignal
    from cios.scoring import SignalScorer

    async with AsyncSessionLocal() as db:
        company = await db.get(PIRCompany, company_id)
        if not company:
            return {"error": "not found"}

        signals_result = await db.execute(
            select(PIRSignal).where(
                PIRSignal.company_id == company_id,
                PIRSignal.tenant_id == tenant_id,
                PIRSignal.is_duplicate.is_(False),
            )
        )
        signals = list(signals_result.scalars().all())

        scorer = SignalScorer()
        scores = scorer.compute(signals)

        # Persist effective weights back to signals
        for sig in signals:
            sig.decay_factor = sig.decay_factor
            sig.effective_weight = sig.effective_weight

        # Update company scores
        company.overall_signal_score = scores["overall_signal_score"]
        company.confidence_score = scores["confidence_score"]
        company.growth_momentum_score = scores["growth_momentum_score"]
        company.government_readiness_score = scores["government_readiness_score"]
        company.priority_tier = scores["priority_tier"]
        company.last_scored_at = datetime.now(UTC)

        await db.commit()

    return {"company_id": str(company_id), **scores}


# ── AI analysis tasks ──────────────────────────────────────────────────────────

@celery_app.task(
    name="cios.tasks.pir.analyze_company_ai",
    queue="analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def analyze_company_ai(
    self,
    company_id: str,
    tenant_id: str,
    analysis_id: str,
    user_id: str | None = None,
) -> dict:
    """Run Claude AI analysis for a company and store results."""
    try:
        return _run(_async_analyze_company(
            uuid.UUID(company_id),
            uuid.UUID(tenant_id),
            uuid.UUID(analysis_id),
            uuid.UUID(user_id) if user_id else None,
        ))
    except Exception as exc:
        log.error("analyze_company_failed", company_id=company_id, error=str(exc))
        raise self.retry(exc=exc)


async def _async_analyze_company(
    company_id: uuid.UUID,
    tenant_id: uuid.UUID,
    analysis_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> dict:
    from cios.core.database import AsyncSessionLocal
    from cios.models.pir import PIRAIAnalysis, PIRCompany, PIRSignal
    from cios.agents.pir_analyst_agent import run_pir_analysis

    async with AsyncSessionLocal() as db:
        analysis = await db.get(PIRAIAnalysis, analysis_id)
        if not analysis:
            return {"error": "Analysis record not found"}

        analysis.status = "running"
        await db.commit()

        company = await db.get(PIRCompany, company_id)
        if not company:
            analysis.status = "failed"
            analysis.error_message = "Company not found"
            await db.commit()
            return {"error": "Company not found"}

        signals_result = await db.execute(
            select(PIRSignal).where(
                PIRSignal.company_id == company_id,
                PIRSignal.tenant_id == tenant_id,
            ).order_by(PIRSignal.detected_at.desc()).limit(50)
        )
        signals = list(signals_result.scalars().all())

        try:
            result = await run_pir_analysis(
                company=company,
                signals=signals,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            analysis.executive_summary = result["executive_summary"]
            analysis.pain_points = result["pain_points"]
            analysis.recommended_outreach = result["recommended_outreach"]
            analysis.buying_probability = result["buying_probability"]
            analysis.suggested_messaging = result["suggested_messaging"]
            analysis.potential_stakeholders = result["potential_stakeholders"]
            analysis.confidence_explanation = result["confidence_explanation"]
            analysis.model_used = "claude-haiku-4-5"
            analysis.status = "completed"
        except Exception as e:
            analysis.status = "failed"
            analysis.error_message = str(e)
            log.error("ai_analysis_error", analysis_id=str(analysis_id), error=str(e))

        await db.commit()

    return {"analysis_id": str(analysis_id), "status": analysis.status}


# ── Scheduled tasks ────────────────────────────────────────────────────────────

@celery_app.task(name="cios.tasks.pir.daily_radar_scan", queue="pir_scan")
def daily_radar_scan() -> dict:
    """Celery Beat task: scan all active tenants' watched companies daily."""
    return _run(_async_daily_scan())


async def _async_daily_scan() -> dict:
    from cios.core.database import AsyncSessionLocal
    from cios.models.pir import PIRCompany
    from sqlalchemy import distinct

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(distinct(PIRCompany.tenant_id)).where(PIRCompany.is_active.is_(True))
        )
        tenant_ids = [str(r[0]) for r in result.fetchall()]

    for tid in tenant_ids:
        # Only scan watched companies in daily run
        bulk_radar_scan.delay(
            tid,
            company_ids=None,
            scan_config={"days_back": 14, "watched_only": True},
        )

    return {"tenants_queued": len(tenant_ids)}
