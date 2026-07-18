# CIOS Agent Architecture

## Design Principles

1. **Evidence-First** — No recommendation without evidence
2. **Traceable** — Every output has a full audit trail
3. **Explainable** — Confidence scores, citations, assumptions always included
4. **Deterministic** — Temperature = 0.0, outputs reproducible
5. **Hierarchical** — CEO synthesizes directors; directors synthesize analysts
6. **Isolated** — No cross-tenant context contamination

## Model Assignment

| Role | Model | Rationale |
|------|-------|-----------|
| CEO Agent | claude-opus-4-8 | Highest reasoning for executive synthesis |
| Award Simulator | claude-opus-4-8 | Complex multi-factor evaluation |
| Director Agents | claude-sonnet-4-6 | Domain expert quality at scale |
| Analyst Agents | claude-haiku-4-5 | High-volume, focused analysis |

## Prompt Engineering Standards

### System Prompt Structure
```
1. Role definition (who the agent is)
2. Jurisdiction/domain expertise declaration
3. Analytical framework (named methodology)
4. Evidence requirements
5. Confidence scoring requirements
6. Regulatory citation requirements
7. Output format specification (always structured JSON)
```

### Output Schema (Recommendation)
```json
{
  "recommendation": "string",
  "confidence_score": 0.0-1.0,
  "evidence": [
    { "source": "string", "content": "string", "relevance": 0.0-1.0 }
  ],
  "rule_citations": [
    { "regulation": "FAR", "section": "15.305(a)", "text": "string" }
  ],
  "assumptions": [
    { "description": "string", "basis": "string", "risk_if_wrong": "low|medium|high" }
  ],
  "risks": [
    { "description": "string", "probability": "low|medium|high", "impact": "low|medium|high" }
  ],
  "alternatives": [
    { "recommendation": "string", "rationale": "string", "confidence": 0.0-1.0 }
  ]
}
```

## Award Simulator Evaluation Framework

### Color/Adjectival Rating Map (DoD)
| Color | Adjective | Score Range | Description |
|-------|-----------|-------------|-------------|
| Blue | Outstanding | 90–100 | Exceeds requirements; very low risk |
| Purple | Good | 75–89 | Exceeds some requirements; low risk |
| Green | Acceptable | 60–74 | Meets requirements; moderate risk |
| Yellow | Marginal | 40–59 | Does not clearly meet; high risk |
| Red | Unacceptable | 0–39 | Fails to meet; cannot be corrected |

### Past Performance Rating (PPIRS)
| Rating | Score |
|--------|-------|
| Exceptional | 5 |
| Very Good | 4 |
| Satisfactory | 3 |
| Marginal | 2 |
| Unsatisfactory | 1 |
| Unknown | N/A |

### Evaluation Methodologies Supported
- FAR 15.101-1 Best Value Tradeoff
- FAR 15.101-2 LPTA
- DoD Source Selection Procedures (Best Value Continuum)
- EU MEAT (Most Economically Advantageous Tender)
- World Bank QCBS / QBS / LCS
- State-level adaptations

## Agent Audit Trail

Every agent invocation creates an `AgentRun` record:
```
AgentRun {
  id: UUID
  agent_type: "ceo_agent" | "director" | "analyst"
  agent_name: "capture_director"
  resource_type: "opportunity" | "simulation" | "bid_decision"
  resource_id: UUID
  status: "pending" | "running" | "completed" | "failed"
  model_used: "claude-opus-4-8"
  prompt_tokens: integer
  completion_tokens: integer
  total_cost_usd: float
  input_snapshot: JSON   -- exact input (reproducibility)
  output: JSON           -- exact output
  rule_pack: string      -- which rule pack was applied
  rule_citations: JSON   -- regulations cited
  duration_ms: integer
}
```

This enables:
- Full reproducibility (replay with same input)
- Token cost tracking per tenant
- Model upgrade impact analysis
- Regulatory compliance demonstration
