"""Base agent framework — evidence-first, explainable-by-design."""
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

import anthropic
import structlog

from cios.config import settings

log = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class Evidence:
    """Every recommendation is grounded in evidence."""
    source: str
    content: str
    relevance: float = 1.0
    citation: str | None = None


@dataclass
class ProcurementRuleCitation:
    rule_pack: str
    regulation: str
    section: str
    text: str
    url: str | None = None


@dataclass
class Assumption:
    description: str
    basis: str
    risk_if_wrong: str = "medium"


@dataclass
class Recommendation:
    """
    The atomic output unit of the CIOS AI system.
    Every recommendation surface is fully auditable.
    """
    title: str
    recommendation: str
    confidence_score: float
    evidence: list[Evidence] = field(default_factory=list)
    rule_citations: list[ProcurementRuleCitation] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    risks: list[dict[str, str]] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    agent_run_id: str | None = None
    reasoning_trace: str | None = None


@dataclass
class AgentContext:
    """Execution context passed through the agent hierarchy."""
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    opportunity_id: uuid.UUID | None = None
    simulation_id: uuid.UUID | None = None
    rule_pack: str = "us_federal_far"
    knowledge_context: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base for all CIOS agents.

    Design principle: Agents never surface conclusions without evidence.
    Every output includes confidence score, rule reference, and assumptions.
    """

    name: str = "base_agent"
    model: str = settings.anthropic_model_director
    max_tokens: int = 4096
    temperature: float = 0.0

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._log = structlog.get_logger(self.__class__.__name__)

    async def run(self, context: AgentContext, **kwargs: Any) -> dict[str, Any]:
        start = time.monotonic()
        run_id = str(uuid.uuid4())

        self._log.info("agent_start", agent=self.name, run_id=run_id, tenant=str(context.tenant_id))

        try:
            result = await self._execute(context, **kwargs)
            duration_ms = int((time.monotonic() - start) * 1000)
            self._log.info(
                "agent_complete",
                agent=self.name,
                run_id=run_id,
                duration_ms=duration_ms,
                tenant=str(context.tenant_id),
            )
            return {"run_id": run_id, "agent": self.name, "result": result, "duration_ms": duration_ms}
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._log.error("agent_error", agent=self.name, run_id=run_id, error=str(e))
            raise

    @abstractmethod
    async def _execute(self, context: AgentContext, **kwargs: Any) -> Any:
        """Implement agent-specific logic."""

    async def _call_claude(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> str:
        """Invoke Claude with structured prompting."""
        messages = [{"role": "user", "content": user_message}]

        kwargs: dict[str, Any] = {
            "model": model or self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""

    def _build_evidence_block(self, evidence: list[dict]) -> str:
        if not evidence:
            return "No direct evidence available. Reasoning from domain knowledge."
        return "\n".join(
            f"[{i+1}] {e.get('source', 'Unknown')}: {e.get('content', '')[:300]}"
            for i, e in enumerate(evidence)
        )
