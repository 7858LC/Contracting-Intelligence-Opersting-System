"""Customer onboarding flow API.

Previously GET /status hardcoded completed_steps: [] and
completion_percentage: 0 always, and POST /steps/{step} validated the step
name and returned "completed" without writing anything to the database —
onboarding "completion" was pure UI theater with nothing behind it. This
persists real progress on Tenant (onboarding_completed_steps/
onboarding_completed_at, see migration 022) and, for every step that maps
to a real model, creates real rows using the same Create schemas and
tables their own dedicated endpoints use (capabilities.py, competitors.py,
teaming.py, past_performance.py) — so a tenant who fills out onboarding
lands on a dashboard that already has their data in it, not an empty one.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from cios.core.dependencies import DB, Auth
from cios.models.capability import Capability
from cios.models.competitor import Competitor
from cios.models.teaming import TeamingPartner
from cios.models.tenant import Tenant

router = APIRouter()


class OnboardingStep(BaseModel):
    step: str
    data: dict[str, Any]


ONBOARDING_STEPS = [
    "company_profile",
    "naics_codes",
    "past_performance",
    "capabilities",
    "certifications",
    "teaming_partners",
    "competitors",
    "preferences",
]

# Tenant columns a "company_profile" step payload may set directly — keeps
# the mapping explicit rather than trusting arbitrary submitted keys onto
# the ORM object.
_COMPANY_PROFILE_FIELDS = {
    "name",
    "cage_code",
    "duns_number",
    "sam_unique_id",
    "small_business_designations",
    "annual_revenue_band",
    "employee_count_band",
    "primary_jurisdictions",
}


class OnboardingStatusResponse(BaseModel):
    steps: list[str]
    completed_steps: list[str]
    completion_percentage: int
    next_step: str | None


class OnboardingStepResponse(BaseModel):
    step: str
    status: str
    next_step: str | None
    onboarding_complete: bool


class OnboardingCompleteResponse(BaseModel):
    status: str
    task_id: str


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user: Auth, db: DB) -> dict:
    tenant = await db.get(Tenant, user.tenant_id)
    completed = list(tenant.onboarding_completed_steps or [])
    return {
        "steps": ONBOARDING_STEPS,
        "completed_steps": completed,
        "completion_percentage": round(100 * len(completed) / len(ONBOARDING_STEPS)),
        "next_step": _next_incomplete_step(completed),
    }


@router.post("/steps/{step_name}", response_model=OnboardingStepResponse)
async def complete_onboarding_step(
    step_name: str, body: OnboardingStep, db: DB, user: Auth
) -> dict:
    if step_name not in ONBOARDING_STEPS:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_name}")

    tenant = await db.get(Tenant, user.tenant_id)
    try:
        await _persist_step(step_name, body.data, tenant, user.tenant_id, db)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    completed = list(tenant.onboarding_completed_steps or [])
    if step_name not in completed:
        completed.append(step_name)
        tenant.onboarding_completed_steps = completed

    onboarding_complete = len(completed) == len(ONBOARDING_STEPS)
    if onboarding_complete and tenant.onboarding_completed_at is None:
        from datetime import UTC, datetime

        tenant.onboarding_completed_at = datetime.now(UTC)
        await db.flush()

        from cios.tasks.onboarding import run_initial_analysis

        run_initial_analysis.delay(str(user.tenant_id))

    return {
        "step": step_name,
        "status": "completed",
        "next_step": _next_incomplete_step(completed),
        "onboarding_complete": onboarding_complete,
    }


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(db: DB, user: Auth) -> dict:
    """Force-complete onboarding (or re-send the welcome summary) without
    needing to have hit every step individually."""
    from datetime import UTC, datetime

    tenant = await db.get(Tenant, user.tenant_id)
    if tenant.onboarding_completed_at is None:
        tenant.onboarding_completed_at = datetime.now(UTC)
        await db.flush()

    from cios.tasks.onboarding import run_initial_analysis

    task = run_initial_analysis.delay(str(user.tenant_id))
    return {"status": "onboarding_complete", "task_id": task.id}


def _next_incomplete_step(completed: list[str]) -> str | None:
    for step in ONBOARDING_STEPS:
        if step not in completed:
            return step
    return None


async def _persist_step(
    step_name: str, data: dict[str, Any], tenant: Tenant, tenant_id, db: DB
) -> None:
    if step_name == "company_profile":
        for field, value in data.items():
            if field in _COMPANY_PROFILE_FIELDS:
                setattr(tenant, field, value)

    elif step_name == "naics_codes":
        codes = data.get("naics_codes", [])
        if isinstance(codes, list):
            tenant.naics_codes = codes

    elif step_name == "past_performance":
        from cios.api.v1.endpoints.past_performance import PastPerformanceCreate
        from cios.models.past_performance import PastPerformance

        for item in data.get("items", []):
            payload = PastPerformanceCreate.model_validate(item)
            db.add(PastPerformance(tenant_id=tenant_id, **payload.model_dump()))

    elif step_name == "capabilities":
        from cios.api.v1.endpoints.capabilities import CapabilityCreate

        for item in data.get("items", []):
            payload = CapabilityCreate.model_validate(item)
            db.add(Capability(tenant_id=tenant_id, **payload.model_dump()))

    elif step_name == "certifications":
        # No standalone Certification model in this codebase — Tenant's
        # generic settings bucket is the right home rather than inventing
        # a table for a handful of strings.
        settings = dict(tenant.settings or {})
        settings["certifications"] = data.get("items", [])
        tenant.settings = settings

    elif step_name == "teaming_partners":
        from cios.api.v1.endpoints.teaming import TeamingPartnerCreate

        for item in data.get("items", []):
            payload = TeamingPartnerCreate.model_validate(item)
            db.add(TeamingPartner(tenant_id=tenant_id, **payload.model_dump()))

    elif step_name == "competitors":
        from cios.api.v1.endpoints.competitors import CompetitorCreate

        for item in data.get("items", []):
            payload = CompetitorCreate.model_validate(item)
            db.add(Competitor(tenant_id=tenant_id, **payload.model_dump()))

    elif step_name == "preferences":
        settings = dict(tenant.settings or {})
        settings.update(data)
        tenant.settings = settings
