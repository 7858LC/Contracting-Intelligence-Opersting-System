"""Sample pre-award evidence package and contractor set.

Used by tests and by the ``POST /winning-profile/sample`` seeding endpoint so the
full vertical slice can be demonstrated end-to-end without external data. The
scenario: a mid-size federal IT modernization + O&M recompete with a security
overlay, a small-business set-aside, and an active incumbent.
"""

from __future__ import annotations

from .schemas import ContractorProfile, EvidenceDoc

SAMPLE_SOLICITATION = {
    "title": "Enterprise IT Modernization & Operations Support (EITMOS)",
    "solicitation_number": "FA8730-26-R-0042",
    "agency": "Department of Veterans Affairs",
    "sub_agency": "Office of Information & Technology",
    "naics_codes": ["541512"],
    "psc_codes": ["D307"],
    "set_aside_type": "SDVOSB Set-Aside",
    "estimated_value": 48_000_000.0,
    "incumbent": "LegacyGov Systems Inc.",
    "rule_pack": "us_federal_far",
}


SAMPLE_DOCUMENTS: list[EvidenceDoc] = [
    EvidenceDoc(
        document_type="sources_sought",
        title="Sources Sought Notice — EITMOS",
        source_ref="Sources Sought Notice, ¶1–4",
        content=(
            "The Department of Veterans Affairs is conducting market research to identify "
            "small business sources capable of providing enterprise IT modernization and "
            "operations support. This effort is anticipated to be issued as an SDVOSB "
            "set-aside. The incumbent contractor currently provides these services under an "
            "existing contract. Respondents must demonstrate relevant experience delivering "
            "cloud migration and cybersecurity services of similar size and scope. "
            "A seamless transition with no disruption to ongoing operations is critical to "
            "the mission."
        ),
    ),
    EvidenceDoc(
        document_type="performance_work_statement",
        title="Performance Work Statement (PWS)",
        source_ref="PWS §1.2, §3.1, §3.4",
        content=(
            "The contractor shall provide enterprise-wide operations support across multiple "
            "locations on a 24/7 basis, requiring significant staffing scale and surge capacity. "
            "The technical approach shall address system integration, cloud migration, and "
            "data analytics. All personnel supporting classified environments must hold an "
            "active Secret clearance; the contractor must maintain compliance with NIST 800-171 "
            "and achieve CMMC Level 2. The program manager shall be PMP-certified and is "
            "designated key personnel. The government seeks modernization through automation and "
            "artificial intelligence where practical."
        ),
    ),
    EvidenceDoc(
        document_type="section_m",
        title="Section M — Evaluation Factors for Award",
        source_ref="Section M, M.2–M.4",
        content=(
            "Award will be made on a best value tradeoff basis. The evaluation factors, in "
            "descending order of importance, are: Factor 1 Technical Approach, Factor 2 Past "
            "Performance, and Factor 3 Price. Past performance is significantly more important "
            "than price. The government will evaluate the recency and relevancy of past "
            "performance references of similar size, scope, and complexity. Under the Technical "
            "Approach factor, the government will assess the offeror's transition and phase-in "
            "plan to ensure continuity of operations with minimal risk."
        ),
    ),
    EvidenceDoc(
        document_type="qa_response",
        title="Pre-Award Questions & Government Responses",
        source_ref="Q&A Set 1, Q7 & Q12",
        content=(
            "Q7: Will the government consider offerors without an active facility clearance? "
            "A7: A facility clearance is required at time of award; personnel security clearances "
            "at the Secret level are mandatory for classified work. "
            "Q12: How important is the transition approach relative to other subfactors? "
            "A12: The transition and phase-in approach is a dominant discriminator; the government "
            "is highly concerned about continuity of operations and knowledge transfer from the "
            "incumbent. Offerors should not underestimate transition risk."
        ),
    ),
    EvidenceDoc(
        document_type="historical_award",
        title="Historical Award Data — Predecessor Contract",
        source_ref="FPDS/USAspending historical record",
        content=(
            "The predecessor contract was awarded to the incumbent, a small business, at a value "
            "consistent with the current estimate. Past performance and a low-risk transition were "
            "cited as decisive in the prior award. The agency has consistently prioritized "
            "cybersecurity and domain expertise in its mission-critical IT programs."
        ),
    ),
]


SAMPLE_CONTRACTORS: list[ContractorProfile] = [
    ContractorProfile(
        name="Meridian Federal Solutions",
        is_self=True,
        is_incumbent=False,
        business_size="small",
        set_asides=["SDVOSB", "Small Business"],
        certifications=["CMMC Level 2", "ISO 9001"],
        clearances=["Secret", "FCL"],
        description=(
            "SDVOSB providing cloud migration, cybersecurity, and system integration to "
            "federal health and defense customers. PMP-certified program managers on staff."
        ),
        capability_text=(
            "cloud migration cybersecurity system integration data analytics automation "
            "nationwide 24/7 operations surge staffing PMP certified program manager "
            "transition phase-in knowledge transfer NIST 800-171"
        ),
        past_performance=[
            {
                "title": "DHA Cloud Migration",
                "description": "Similar size and scope cloud "
                "migration and O&M with a clean CPARS and successful phase-in.",
            },
        ],
    ),
    ContractorProfile(
        name="LegacyGov Systems Inc.",
        is_incumbent=True,
        business_size="small",
        set_asides=["SDVOSB"],
        certifications=["CMMC Level 2"],
        clearances=["Secret", "FCL"],
        description="Incumbent provider of the enterprise IT operations support contract.",
        capability_text=(
            "incumbent operations support cybersecurity domain expertise mission knowledge "
            "24/7 nationwide staffing PMP program manager past performance CPARS"
        ),
        past_performance=[
            {
                "title": "EITMOS (incumbent)",
                "description": "Directly relevant incumbent performance on this exact requirement.",
            },
        ],
    ),
    ContractorProfile(
        name="Apex Digital Partners",
        is_incumbent=False,
        business_size="large",
        set_asides=[],
        certifications=["ISO 9001"],
        clearances=[],
        description=(
            "Large commercial digital transformation firm with strong AI/automation offerings "
            "but limited federal past performance and no set-aside status."
        ),
        capability_text=(
            "artificial intelligence machine learning automation digital transformation "
            "cloud analytics innovation modernization"
        ),
        past_performance=[
            {
                "title": "Commercial AI Platform",
                "description": "Commercial modernization; limited directly-relevant federal CPARS.",
            },
        ],
    ),
]
