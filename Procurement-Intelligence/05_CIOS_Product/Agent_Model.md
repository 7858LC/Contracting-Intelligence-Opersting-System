# UzimaAmka Agent Model

## The Hierarchical Intelligence Architecture

The UzimaAmka platform uses a three-tier AI agent hierarchy modeled loosely on organizational structure: strategic leadership → functional directors → specialist analysts.

Users interact only with the output layer. Agent orchestration, delegation, and internal reasoning are never surfaced to users — only the final recommendation with its evidence structure.

---

## Tier 1: CEO Agent
*Model: Claude Opus 4.8*

**Role:** Strategic synthesis and final recommendation authority.

**Responsibilities:**
- Final bid/no-bid recommendation with full evidence summary
- Award probability synthesis across all intelligence domains
- Award simulation gate review (Approve / Revise Before Submit / Do Not Submit)
- Executive briefing generation for leadership review
- Cross-opportunity portfolio analysis and resource allocation guidance

**Invocation:** Triggered for all high-stakes decisions: bid decisions, award simulations, and strategic portfolio reviews.

**Output structure:**
```json
{
  "recommendation": "BID | NO_BID | CONDITIONAL",
  "confidence_score": 0.78,
  "executive_summary": "...",
  "evidence": [{"source": "...", "finding": "...", "weight": "high"}],
  "key_assumptions": ["..."],
  "risks": ["..."],
  "alternatives_considered": ["..."],
  "rule_citations": ["FAR 15.305(a)"],
  "model_version": "claude-opus-4-8"
}
```

---

## Tier 2: Director Agents
*Model: Claude Sonnet 4.6*

**Opportunity Intelligence Director**
- Processes incoming opportunities from all sources
- Extracts structured intelligence (agency, requirements, value, timeline, set-aside)
- Scores opportunity attractiveness across 12 dimensions
- Routes to relevant Analyst Agents for deep processing

**Competitive Intelligence Director**
- Synthesizes competitor profiles from award histories, protest decisions, pricing data
- Identifies incumbent vulnerabilities
- Develops competitive counter-strategies
- Maintains real-time competitor intelligence updates

**Past Performance Director**
- Indexes firm past performance against opportunity requirements
- Calculates relevance scores using FAR evaluation analogies
- Identifies capability gaps requiring teaming or organic development
- Recommends past performance reference prioritization

**Teaming Strategy Director**
- Analyzes capability gaps requiring teaming partners
- Identifies optimal partners from known partner registry and award history
- Models teaming agreement structures and risk allocation
- Assesses socioeconomic positioning for set-aside strategy

---

## Tier 3: Analyst Agents
*Model: Claude Haiku 4.5*

High-volume, narrow-task specialists:
- **Document Analyst:** Extracts structured data from solicitations, PWS, SOW documents
- **Award History Analyst:** Processes USASpending.gov award records for patterns
- **Pricing Analyst:** Benchmarks labor rates and contract pricing against market
- **Compliance Analyst:** Checks opportunities against firm qualification criteria
- **News Analyst:** Monitors agency news for relevant procurement signals

---

## Agent Coordination Protocol

1. User action triggers CEO Agent or Director Agent invocation
2. Director receives task, decomposes into sub-tasks
3. Director dispatches sub-tasks to relevant Analyst Agents
4. Analysts return structured results within defined schemas
5. Director synthesizes analyst outputs into coherent intelligence
6. CEO Agent (for strategic decisions) receives Director outputs and produces final recommendation
7. All agent reasoning, intermediate outputs, and tool calls are logged but not surfaced to user
8. User receives only: recommendation + evidence + confidence + citations
