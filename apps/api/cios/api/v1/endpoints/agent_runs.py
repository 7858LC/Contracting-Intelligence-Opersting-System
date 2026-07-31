"""Agent Runs audit trail API — immutable evidence trail."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from cios.core.dependencies import DB, Auth
from cios.models.agent_run import AgentRun, AgentRunStep

router = APIRouter()


class AgentRunSummaryResponse(BaseModel):
    id: uuid.UUID
    agent_type: str
    agent_name: str
    status: str
    resource_type: str
    resource_id: uuid.UUID | None
    duration_ms: int | None
    model_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunListResponse(BaseModel):
    items: list[AgentRunSummaryResponse]


class AgentRunStepResponse(BaseModel):
    id: uuid.UUID
    step_index: int
    step_name: str
    agent_name: str
    status: str
    input_data: dict[str, Any] | None
    output_data: dict[str, Any] | None
    reasoning: str | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunDetailResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_type: str
    agent_name: str
    resource_type: str
    resource_id: uuid.UUID | None
    triggered_by: uuid.UUID | None
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    model_used: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_cost_usd: float | None
    output: dict[str, Any] | None
    error_message: str | None
    rule_pack: str | None
    rule_citations: list
    input_snapshot: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    steps: list[AgentRunStepResponse]

    model_config = {"from_attributes": True}


@router.get("", response_model=AgentRunListResponse)
async def list_agent_runs(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.tenant_id == user.tenant_id)
        .order_by(AgentRun.created_at.desc())
        .limit(100)
    )
    return {"items": result.scalars().all()}


@router.get("/{run_id}", response_model=AgentRunDetailResponse)
async def get_agent_run(run_id: uuid.UUID, db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.tenant_id == user.tenant_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    steps_result = await db.execute(
        select(AgentRunStep)
        .where(AgentRunStep.agent_run_id == run_id)
        .order_by(AgentRunStep.step_index)
    )

    return AgentRunDetailResponse.model_validate(
        {**run.to_dict(), "steps": steps_result.scalars().all()}
    )
