"""Winning Profile Hypothesis™ Engine — CIOS pre-award intelligence layer.

Public surface for the evidence-fusion pipeline that infers what an ideal awardee
would most likely need, compares contractors against that hypothesis, and produces
an executive pursuit-decision assessment — all before proposal development begins.
"""
from .engine import IntelligenceResult, WinningProfileEngine
from .schemas import (
    Assessment,
    AttributeAlignment,
    CapabilityGap,
    ContractorAlignment,
    ContractorProfile,
    EvidenceDoc,
    ExtractedSignal,
    GapClosure,
    InferredAttribute,
    WinningProfile,
)

__all__ = [
    "WinningProfileEngine",
    "IntelligenceResult",
    "EvidenceDoc",
    "ExtractedSignal",
    "InferredAttribute",
    "WinningProfile",
    "ContractorProfile",
    "AttributeAlignment",
    "CapabilityGap",
    "GapClosure",
    "ContractorAlignment",
    "Assessment",
]
