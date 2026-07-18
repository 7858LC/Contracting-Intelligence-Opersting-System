"""Tests for the Procurement Rule Engine."""
import pytest
from cios.procurement_rules.registry import RulePackRegistry, US_FEDERAL_FAR, WORLD_BANK


def test_registry_returns_known_pack():
    registry = RulePackRegistry()
    pack = registry.get("us_federal_far")
    assert pack is not None
    assert pack.id == "us_federal_far"
    assert pack.jurisdiction == "federal"


def test_registry_returns_none_for_unknown_pack():
    registry = RulePackRegistry()
    assert registry.get("unknown_pack") is None


def test_registry_lists_all_packs():
    registry = RulePackRegistry()
    packs = registry.list_packs()
    assert len(packs) >= 4
    ids = [p["id"] for p in packs]
    assert "us_federal_far" in ids
    assert "us_federal_dfars" in ids
    assert "eu_public_procurement" in ids
    assert "world_bank" in ids


def test_us_federal_far_evaluation_factors():
    registry = RulePackRegistry()
    factors = registry.get_evaluation_factors("us_federal_far")
    assert len(factors) == 4
    weights = [f["weight"] for f in factors]
    assert abs(sum(weights) - 1.0) < 0.001, "Weights must sum to 1.0"


def test_world_bank_evaluation_factors():
    registry = RulePackRegistry()
    factors = registry.get_evaluation_factors("world_bank")
    assert len(factors) == 2
    technical = next(f for f in factors if f["type"] == "technical")
    assert technical["weight"] == 0.70


def test_us_federal_far_mandatory_requirements():
    assert "SAM.gov registration active" in US_FEDERAL_FAR.mandatory_requirements


def test_far_thresholds():
    assert US_FEDERAL_FAR.thresholds["micro_purchase"] == 10_000
    assert US_FEDERAL_FAR.thresholds["simplified_acquisition"] == 250_000


def test_world_bank_methodologies():
    assert "QCBS" in WORLD_BANK.evaluation_methodologies
    assert "QBS" in WORLD_BANK.evaluation_methodologies
