# UzimaAmka Security Model

## Security Philosophy

Government contractors handle sensitive procurement information: competitive strategy, pricing, agency relationships, proprietary capture intelligence. A Procurement Intelligence platform that cannot be trusted with this information is useless.

Our security model is designed to be as rigorous as the data it protects.

## Zero Trust Architecture

Every request is treated as potentially hostile until proven otherwise:

- **No implicit trust** — No request is trusted based on network location or previous authentication
- **Verify explicitly** — Every API request validates a JWT token, verifies tenant membership, and enforces resource-level authorization
- **Least privilege** — Users can access only the data and functions their role explicitly authorizes
- **Assume breach** — Logging, monitoring, and alerting designed to detect compromise, not just prevent it

## Tenant Isolation Architecture

Multi-tenancy with complete data isolation:

### Database Layer
- PostgreSQL Row-Level Security (RLS) on every tenant-scoped table
- RLS policy enforced via `app.current_tenant` session variable
- No application-layer filtering trusted as sole isolation mechanism
- Tenant ID validated at both application and database layers

### Vector Store Layer
- Dedicated Qdrant collection per tenant: `cios_tenant_{uuid}`
- No cross-collection queries permitted
- Collection names contain no business-sensitive information
- Collection deletion triggered on tenant offboarding

### Encryption
- Data at rest: AES-256 encryption at the storage layer
- Data in transit: TLS 1.3 minimum
- Per-tenant encryption keys: PBKDF2-derived Fernet keys from tenant UUID + master key
- Enterprise option: Customer-managed keys (CMK) via AWS KMS

## Authentication & Authorization

| Mechanism | Implementation |
|---|---|
| Authentication | JWT tokens (access + refresh) with 1-hour expiry |
| Token refresh | Automatic on 401, redirect to login on refresh failure |
| Authorization | Role-based (admin / member / read-only) |
| API keys | Scoped per-tenant, hashed before storage, shown once |
| MFA | TOTP support (Enterprise tier) |
| SSO | SAML 2.0 (Enterprise tier) |

## Audit Logging

Every data access and mutation is logged with:
- Tenant ID, User ID, timestamp
- Action type and resource type/ID
- Changes (before/after for mutations)
- IP address, user agent
- Request ID for cross-service tracing

Audit logs are immutable (append-only), retained for 7 years, and exportable for compliance review.

**Critical rule: Audit logs never contain tenant data content — only IDs and action metadata.**

## Compliance Alignment

| Standard | Status |
|---|---|
| SOC 2 Type II | Architecture designed for certification |
| NIST 800-171 | Controls mapped; gap assessment available |
| CMMC Level 2 | Aligned for DoD contractor customers |
| GDPR | Data residency options; DPA available |
| FedRAMP Moderate | Compatible infrastructure patterns |

## AI Security Considerations

- Prompt injection protection: All user-provided content is treated as data, not instructions, in AI contexts
- No customer data used for model training without explicit opt-in
- AI model outputs logged with model version for auditability
- Confidence scores and evidence citations required on all AI recommendations — no black-box outputs surfaced to users
- Rate limiting on AI-intensive endpoints to prevent abuse
