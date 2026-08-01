# CUI / Classified / Export-Controlled Data — Draft Restriction Language

**Status: DRAFT FOR COUNSEL REVIEW. Not legal advice. Do not publish or rely
on this text until reviewed and approved by qualified counsel.**

## Why this exists

CIOS is a commercial SaaS platform for government contractors, not a
government system of record (see root `CLAUDE.md`, "Commercial SaaS, not a
federal system of record"). It derives decision intelligence from public
procurement data and customer-owned business inputs only, and is not built,
authorized, or accredited to store or process Controlled Unclassified
Information (CUI, per 32 CFR Part 2002), classified national security
information, or export-controlled technical data (ITAR/EAR). That statement
previously existed only as an internal engineering note with no contractual
or technical backing. This draft is the contractual half of turning it into
an enforceable position; `apps/api/cios/core/cui_screening.py` and the
upload-time attestation in `apps/api/cios/api/v1/endpoints/knowledge_vault.py`
are the technical half.

## 1. Proposed Acceptable Use Policy / ToS clause

> **Prohibited Data.** Customer shall not upload, transmit, input, or
> otherwise submit to the Service any of the following ("Prohibited Data"):
> (a) Controlled Unclassified Information as defined by 32 C.F.R. Part 2002
> and any agency-specific CUI category; (b) classified national security
> information under Executive Order 13526 or any successor order; (c)
> technical data or information subject to the International Traffic in
> Arms Regulations (ITAR, 22 C.F.R. Parts 120–130) or the Export
> Administration Regulations (EAR, 15 C.F.R. Parts 730–774); or (d) any
> other data Customer is prohibited by law, regulation, or contract from
> disclosing to a third party or processing outside a government-accredited
> or specifically authorized system.
>
> The Service is not designed, accredited, or authorized to receive,
> store, or process Prohibited Data, including via the Service's use of
> third-party AI model providers to analyze Customer-submitted content.
> Customer is solely responsible for ensuring that content it submits to
> the Service does not constitute Prohibited Data, and Customer shall
> indemnify, defend, and hold harmless [Company] from and against any
> claim, loss, liability, fine, or regulatory action arising from
> Customer's breach of this provision.
>
> [Company] reserves the right to (i) implement automated or manual
> screening for markings indicative of Prohibited Data and reject or
> quarantine content bearing such markings, (ii) suspend or terminate
> Customer's account for actual or suspected submission of Prohibited
> Data, and (iii) report suspected submissions of classified information
> to the appropriate government authority where legally required.

**Open questions for counsel:**
- Whether indemnification should be mutual, capped, or carved out of any
  general liability cap elsewhere in the MSA.
- Whether "Company reserves the right to report... to the appropriate
  government authority" creates any obligation (vs. discretion) we want to
  avoid committing to contractually.
- Whether this belongs in the MSA/ToS directly or in a separate Acceptable
  Use Policy incorporated by reference (affects how it's amended later).
- Whether EAR/ITAR should be called out only for the technical-data
  subcategory the platform could plausibly encounter (government
  contractor proposal/capture content), rather than the full regulatory
  scope, to avoid over-promising a compliance posture the platform doesn't
  have.

## 2. Proposed upload-time attestation copy (paired with the checkbox in
   `knowledge-vault-view.tsx`)

> I confirm this document does not contain Controlled Unclassified
> Information (CUI), classified information, or export-controlled
> (ITAR/EAR) technical data.

This is the UI-facing string tied to the required `attestation` field on
`POST /knowledge-vault/upload`. Every upload records an `AuditLog` entry
capturing that this box was checked, by whom, and when — see
`cios/api/v1/endpoints/knowledge_vault.py`.

## 3. What this combination does and does not protect against

(For context — not for the ToS itself.)

- **Protects:** Gives CIOS a documented, logged representation from the
  customer for every upload, plus a code-level backstop that catches
  documents carrying common CUI/classification banner markings before
  they're stored or processed. Establishes a "reasonable steps taken"
  posture if a dispute or audit ever arises.
- **Does not protect against:** Unmarked CUI (marking is inconsistently
  applied in practice), a customer who checks the box falsely, or any
  claim that CIOS's infrastructure is authorized to handle CUI under
  DFARS 252.204-7012 / NIST SP 800-171 / CMMC. This is risk-reduction and
  contractual risk-shifting, not a compliance program. If CIOS pursues
  customers with meaningful CUI exposure, a real NIST 800-171 posture
  would need to be evaluated separately — out of scope here.
