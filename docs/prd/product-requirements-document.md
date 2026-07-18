# CIOS — Product Requirements Document
**Version:** 1.0.0 | **Classification:** Internal | **Date:** 2026-07-18

---

## 1. Product Vision

**Contract Intelligence Operating System (CIOS)** is the world's first Procurement Intelligence Platform.

CIOS is NOT:
- Proposal writing software
- CRM
- Document management

CIOS IS:
- An executive decision platform that increases the probability of winning public-sector contracts **before proposal development begins**
- The Bloomberg Terminal of procurement

### Mission
Increase award probability. Reduce bid costs. Improve bid/no-bid decisions. Identify capability gaps. Recommend teaming strategies. Simulate source selection. Continuously improve organizational capture intelligence.

---

## 2. Target Market

### Primary Market
Mid-market and large government contractors ($10M–$500M revenue) pursuing:
- Federal contracts (FAR/DFARS)
- State and local contracts
- Defense contracts (CMMC/NIST 800-171)

### Secondary Market
- International government contractors (EU, World Bank)
- Tribal entities
- Education institutions (2 CFR 200)
- Healthcare contractors (CMS)
- Utility contractors

### Market Size
- US government contracting: $700B+ annual spend
- Addressable SMB and mid-market: ~$200B
- Capture management software TAM: ~$2B

---

## 3. Core Philosophy

The customer is never told how to run their business.

Every CIOS recommendation includes:
1. **Evidence** — specific data supporting the recommendation
2. **Confidence Score** — 0.0–1.0, never overstate certainty
3. **Applicable Procurement Rule** — FAR citation, DFARS section, state code
4. **Assumptions** — explicit list of what we assumed
5. **Risk** — what could go wrong
6. **Alternatives** — at least one alternative recommendation

---

## 4. System Modules

### Module 01: Opportunity Intelligence
**Purpose:** Automated discovery and intelligence extraction  
**Inputs:** SAM.gov feeds, state portals, custom RSS, manual entry  
**Outputs:** Enriched opportunity records with AI-extracted requirements, evaluation criteria, and competitive signals  
**Key AI Tasks:** Requirements extraction, evaluation criteria parsing, incumbent identification, competitive intensity scoring  

### Module 02: Bid / No-Bid Engine
**Purpose:** Evidence-based go/no-go decision support  
**Scoring Dimensions (8):**
1. Strategic Fit (20%)
2. Win Probability (20%)
3. Past Performance Alignment (15%)
4. Capability Match (15%)
5. Competitive Position (10%)
6. Cost of Bid vs. ROI (10%)
7. Risk Profile (5%)
8. Relationship Strength (5%)

**Output:** Weighted composite score, recommendation, rationale, alternatives

### Module 03: Procurement Rule Engine
**Purpose:** Jurisdiction-agnostic rule enforcement  
**Rule Packs:**
- `us_federal_far` — FAR Parts 1–53
- `us_federal_dfars` — DFARS + DARS + agency supplements
- `state_generic` — Uniform Procurement Act
- `eu_public_procurement` — EU Directive 2014/24/EU
- `world_bank` — IPF Borrower Procurement Regulations
- Custom rule packs (Enterprise)

### Module 04: Compliance Engine
**Purpose:** Mandatory requirements verification  
**Checks:**
- SAM.gov registration status
- NAICS code eligibility
- Set-aside eligibility (8(a), SDVOSB, HUBZone, WOSB)
- Security clearance requirements
- CMMC level requirements
- Certifications and licenses
- Insurance requirements
- Financial responsibility thresholds

### Module 05: Capability Gap Analysis
**Purpose:** Map solicitation requirements to organizational capabilities  
**Methodology:** NLP-based requirement extraction → vector similarity match → gap scoring → remediation options

### Module 06: Past Performance Intelligence
**Purpose:** Smart relevance scoring and narrative assistance  
**Key Features:**
- Relevance scoring against active opportunities
- CPARS rating tracking
- Narrative generation assistance
- Recency and dollar-value weighting
- Technology/domain similarity scoring

### Module 07: Teaming Recommendation Engine
**Purpose:** Optimize team composition for win probability  
**Analysis:**
- Gap-filling partner identification
- Small business strategy optimization
- Historical teaming success analysis
- Partner risk assessment
- Relationship strength mapping

### Module 08: Competitive Intelligence
**Purpose:** Know your competition before they know you're bidding  
**Sources:** USASpending.gov, FPDS-NG, SAM.gov, SEC filings, public press releases  
**Outputs:** Competitor profiles, win rate estimates, pricing tendencies, incumbent vulnerability assessment

### Module 09: Value Proposition Builder
**Purpose:** Differentiated positioning for each opportunity  
**Output:** Tailored discriminator set with evidence from Knowledge Vault

### Module 10: Executive Capture Dashboard
**Purpose:** Board-level pipeline visibility  
**KPIs:** Weighted pipeline value, win probability distribution, bid/no-bid ratio, cost per win, ROI by market segment

### Module 11: Proposal Readiness Score
**Purpose:** Assess readiness before writing begins  
**Dimensions:** Past performance quality, team bios, technical approach, management plan, price competitiveness, compliance documentation

### Module 12: Award Probability Engine
**Purpose:** ML-powered win probability  
**Inputs:** Bid history, competitive landscape, agency relationship, solution strength, pricing position  
**Output:** Probability score with confidence interval and evidence chain

### Module 13: Award Simulator (FLAGSHIP)
**Purpose:** Emulate government source selection evaluation  
**Process:** Upload solicitation → AI evaluates as government SSA/SSEB → Red team commentary → Improvement roadmap  
**Output:** Technical score, management score, past performance rating, risk rating, price competitiveness, award probability, gate review recommendation

### Module 14: Lessons Learned Knowledge Vault
**Purpose:** Capture and apply institutional knowledge  
**Capture Events:** Post-award debrief, loss debrief, teaming debrief, process improvements

### Module 15: Organizational Intelligence
**Purpose:** Continuously improve organizational capture posture  
**Analytics:** Win/loss trends, capability growth tracking, market penetration analysis, BD ROI

---

## 5. AI Organization

### Orchestration Hierarchy

```
CEO Agent (claude-opus-4-8)
├── Capture Director (claude-sonnet-4-6)
│   ├── Bid Analysis Analyst
│   ├── Award Probability Analyst
│   └── Proposal Readiness Analyst
├── Compliance Director (claude-sonnet-4-6)
│   ├── FAR/DFARS Compliance Analyst
│   ├── CMMC/NIST Analyst
│   └── Set-Aside Eligibility Analyst
├── Agency Intelligence Director (claude-sonnet-4-6)
│   ├── Agency Relationship Analyst
│   ├── Program Office Intelligence Analyst
│   └── Requirements Prediction Analyst
├── Technical Director (claude-sonnet-4-6)
│   ├── Requirements Analyst
│   ├── Capability Gap Analyst
│   └── Technical Approach Analyst
├── Pricing Director (claude-sonnet-4-6)
│   ├── Price-to-Win Analyst
│   ├── Cost Structure Analyst
│   └── Market Pricing Analyst
├── Competitive Intelligence Director (claude-sonnet-4-6)
│   ├── Incumbent Analysis Analyst
│   ├── Competitor Profiling Analyst
│   └── Win Pattern Analyst
├── Risk Director (claude-sonnet-4-6)
│   ├── Technical Risk Analyst
│   ├── Programmatic Risk Analyst
│   └── Financial Risk Analyst
├── Proposal Director (claude-sonnet-4-6)
│   ├── Section Writer Analyst
│   ├── Theme Development Analyst
│   └── Red Team Analyst
└── Executive Review Board
    ├── Gate Review Agent
    └── Portfolio Strategy Agent
```

### Design Principles
- Users NEVER interact directly with agents
- Users see only recommendations, never raw agent outputs
- Every recommendation is fully auditable
- Model version pinned at recommendation time
- Confidence scores required on all outputs

---

## 6. Knowledge Vault Architecture

### Per-Tenant Private Memory
Each customer owns a completely isolated knowledge store:
- Private Qdrant vector collection
- Encrypted at rest with tenant-derived key
- Never shared across tenants
- Immutable audit trail of all access

### Document Types
| Type | Description |
|------|-------------|
| `past_performance` | Contract performance records |
| `capability_statement` | Company capability documents |
| `proposal` | Previous proposals (win/loss) |
| `resume` | Key personnel resumes |
| `certification` | Business certifications |
| `policy` | Company policies and procedures |
| `pricing` | Rate cards and cost models |
| `lessons_learned` | Post-award/debrief notes |
| `teaming_agreement` | NDA, teaming agreements |
| `evaluation` | Debrief letters |
| `general` | General documents |

---

## 7. Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| Authentication | JWT + refresh tokens, optional SSO/SAML |
| Authorization | Role-based (owner/admin/member) + row-level security |
| Tenant Isolation | PostgreSQL RLS + per-tenant Qdrant collection |
| Data Encryption | AES-256 at rest, TLS 1.3 in transit |
| Field Encryption | Fernet encryption for sensitive fields |
| Customer Keys | Enterprise: BYOK via AWS KMS |
| Audit Trail | Immutable audit_logs table, append-only |
| NIST 800-171 | 110 controls mapped (see security-controls.md) |
| CMMC Level 2 | 110 NIST 800-171 practices implemented |
| SOC 2 Type II | Controls designed for Type II certification |
| FedRAMP | Moderate baseline architecture |

---

## 8. Pricing Strategy

### Starter — $499/month
- 50 opportunities
- 5 award simulations/month
- 500MB knowledge vault
- 3 user seats
- Award Simulator
- Email support
- 14-day free trial

### Professional — $1,499/month
- 500 opportunities
- 50 award simulations/month
- 5GB knowledge vault
- 10 user seats
- Competitive Intelligence module
- API access
- Priority support
- 14-day free trial

### Enterprise — Custom pricing
- Unlimited opportunities
- Unlimited simulations
- Unlimited storage
- Unlimited seats
- Customer-owned encryption keys
- SSO/SAML
- Dedicated customer success manager
- Custom rule packs
- On-premise deployment option
- SLA: 99.9% uptime

---

## 9. Success Metrics

### Customer Success KPIs
- Win rate improvement (baseline vs. 12-month post-adoption)
- Bid cost reduction
- Bid/no-bid accuracy (% of no-bids that would have been losses)
- Time-to-decision reduction
- Proposal readiness score at submission

### Platform KPIs
- MRR growth
- Net Revenue Retention (target: >110%)
- Churn rate (target: <5% annual)
- Simulations per active tenant per month
- Knowledge Vault documents ingested

---

## 10. Roadmap

### Phase 1 — Foundation (Months 1–3) ✅
- Core platform architecture
- Modules 1, 2, 5, 6, 7, 8, 13
- Knowledge Vault
- Award Simulator (flagship)
- Multi-tenant auth
- Stripe billing

### Phase 2 — Intelligence Expansion (Months 4–6)
- SAM.gov automated ingestion
- FPDS award history import
- USASpending.gov integration
- Real-time opportunity monitoring
- Email/Slack notification system
- Mobile app (iOS/Android)

### Phase 3 — Market Expansion (Months 7–12)
- State/local procurement portals
- EU procurement directive support
- World Bank procurement integration
- Tribal government module
- Custom rule pack builder
- White-label offering

### Phase 4 — Enterprise Scale (Months 13–18)
- FedRAMP authorization
- CMMC certification
- On-premise deployment
- Enterprise SSO/SAML
- Advanced analytics platform
- Proposal writing assistant (Module 9 expansion)
