"""Best-effort screening for CUI / classification / export-control markings.

CIOS is a commercial SaaS platform for government contractors, not a
government system of record (see root CLAUDE.md, "Commercial SaaS, not a
federal system of record") — it is not built, accredited, or authorized to
store or process CUI, classified information, or export-controlled
technical data. This module is the technical backstop for that: a scan for
the banner markings that appear on documents actually carrying those
designations (DFARS CUI legends, classification banners, distribution
statements, export-control legends).

This catches the common failure mode — a marked document uploaded by
mistake — not unmarked content that happens to be controlled; marking is
inconsistently applied in practice, and that gap is a policy/attestation
problem (see the required attestation in knowledge_vault.py's upload
endpoint), not a pattern-matching one. See docs/legal/cui-restriction-draft.md
for the full reasoning and the paired ToS/attestation language.
"""

import re

# CUI/NOFORN/ITAR are case-sensitive: real markings are always presented
# in full caps, and matching lowercase would false-positive on ordinary
# English words and acronyms. Multi-word phrases are distinctive enough
# that case-insensitive matching doesn't meaningfully raise false positives.
_PATTERNS: dict[str, re.Pattern[str]] = {
    "CUI": re.compile(r"\bCUI\b"),
    "CONTROLLED_UNCLASSIFIED_INFORMATION": re.compile(
        r"CONTROLLED\s+UNCLASSIFIED\s+INFORMATION", re.IGNORECASE
    ),
    "FOUO": re.compile(r"\bFOUO\b|FOR\s+OFFICIAL\s+USE\s+ONLY", re.IGNORECASE),
    "NOFORN": re.compile(r"\bNOFORN\b"),
    "TOP_SECRET": re.compile(r"TOP\s+SECRET", re.IGNORECASE),
    "SECRET_BANNER": re.compile(r"\bSECRET//"),
    "CONFIDENTIAL_BANNER": re.compile(r"\bCONFIDENTIAL//"),
    "EXPORT_CONTROLLED": re.compile(r"EXPORT\s+CONTROLLED", re.IGNORECASE),
    "ITAR": re.compile(r"\bITAR\b"),
    "RESTRICTED_DISTRIBUTION": re.compile(
        r"DISTRIBUTION\s+STATEMENT\s+[B-F]\b", re.IGNORECASE
    ),
}


def scan_for_restricted_markings(text: str) -> list[str]:
    """Returns the labels of every marking pattern found in `text`, empty
    if none matched. Callers should treat a non-empty result as "block and
    quarantine", not "definitely CUI" — this is a heuristic marking scan,
    not a content classifier."""
    if not text:
        return []
    return [label for label, pattern in _PATTERNS.items() if pattern.search(text)]
