"""Customer onboarding flow API."""

from fastapi import APIRouter
from pydantic import BaseModel

from cios.core.dependencies import DB, AdminAuth, Auth

router = APIRouter()


class OnboardingStep(BaseModel):
    step: str
    data: dict


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


class OnboardingStatusResponse(BaseModel):
    steps: list[str]
    completed_steps: list[str]
    completion_percentage: int
    next_step: str | None


class OnboardingStepResponse(BaseModel):
    step: str
    status: str
    next_step: str | None


class OnboardingCompleteResponse(BaseModel):
    status: str
    task_id: str


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user: Auth) -> dict:
    """Return onboarding completion status."""
    return {
        "steps": ONBOARDING_STEPS,
        "completed_steps": [],
        "completion_percentage": 0,
        "next_step": "company_profile",
    }


@router.post("/steps/{step_name}", response_model=OnboardingStepResponse)
async def complete_onboarding_step(
    step_name: str, body: OnboardingStep, db: DB, user: Auth
) -> dict:
    if step_name not in ONBOARDING_STEPS:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"Unknown step: {step_name}")

    return {"step": step_name, "status": "completed", "next_step": _next_step(step_name)}


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(db: DB, user: AdminAuth) -> dict:
    """Mark onboarding complete and trigger initial AI analysis."""
    from cios.tasks.onboarding import run_initial_analysis

    task = run_initial_analysis.delay(str(user.tenant_id))
    return {"status": "onboarding_complete", "task_id": task.id}


def _next_step(current: str) -> str | None:
    idx = ONBOARDING_STEPS.index(current) if current in ONBOARDING_STEPS else -1
    if idx < len(ONBOARDING_STEPS) - 1:
        return ONBOARDING_STEPS[idx + 1]
    return None
