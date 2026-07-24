"""
Procurement Rule Engine — jurisdiction-specific rule packs.

The system is procurement-framework driven, NOT government-specific.
Universal procurement concepts are implemented here, with
jurisdiction-specific overrides in each rule pack.
"""

from .registry import RulePackRegistry

registry = RulePackRegistry()
