"""Agent Runs audit trail API — immutable evidence trail."""
import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from cios.core.dependencies import Auth, DB
from cios.models.agent_run import AgentRun, AgentRunStep

router = APIRouter()


@router.get("")
async def list_agent_runs(db: DB, user: Auth) -> dict:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.tenant_id == user.tenant_id)
        .order_by(AgentRun.created_at.desc())
        .limit(100)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "agent_type": r.agent_type,
                "agent_name": r.agent_name,
                "status": r.status,
                "resource_type": r.resource_type,
                "resource_id": str(r.resource_id) if r.resource_id else None,
                "duration_ms": r.duration_ms,
                "model_used": r.model_used,
                "created_at": r.created_at.isoformat(),
            }
            for r in items
        ]
    }


@router.get("/{run_id}")
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

    return {
        **run.to_dict(),
        "steps": [s.to_dict() for s in steps_result.scalars().all()],
    }
