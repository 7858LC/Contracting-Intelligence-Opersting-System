"""SAMGovScanner must actually search SAM.gov by the target company's name.

Regression test for a bug where scan() ignored the `keywords` argument
entirely and only filtered SAM.gov's entity API by NAICS code (which the
"Add Company" flow doesn't even collect). That meant scanning a specific
company like Leidos never queried SAM.gov for that company at all — it
just pulled an arbitrary batch of up to 100 active entities and hoped the
target happened to be in it, which an established registrant that isn't
freshly registering/updating almost never is.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://cios_user:cios_pass@localhost/x")
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")

from unittest.mock import AsyncMock, MagicMock

from cios.config import settings
from cios.scanners.samgov import SAMGovScanner


def _empty_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


async def test_scan_passes_company_name_as_legal_business_name_filter():
    scanner = SAMGovScanner(api_key="TEST_KEY")
    scanner._get = AsyncMock(  # type: ignore[method-assign]
        return_value=_empty_response({"entityData": []})
    )

    await scanner.scan(keywords=["Leidos", "leidos"], naics_codes=[], days_back=30)

    entity_call = scanner._get.call_args_list[0]
    params = entity_call.kwargs["params"]
    assert params["legalBusinessName"] == "Leidos"


async def test_scan_with_no_keywords_omits_name_filter():
    scanner = SAMGovScanner(api_key="TEST_KEY")
    scanner._get = AsyncMock(  # type: ignore[method-assign]
        return_value=_empty_response({"entityData": []})
    )

    await scanner.scan(keywords=[], naics_codes=["541511"], days_back=30)

    entity_call = scanner._get.call_args_list[0]
    params = entity_call.kwargs["params"]
    assert "legalBusinessName" not in params
    assert params["naicsCode"] == "541511"


def test_falls_back_to_demo_key_when_setting_is_unset():
    """Regression test: settings.sam_gov_api_key is a real Pydantic field
    defaulting to "" — it always exists, so the old
    getattr(settings, "sam_gov_api_key", "DEMO_KEY") could never actually
    fall through to DEMO_KEY when the env var was left unconfigured (that
    default only applies to a genuinely missing attribute). Every request
    went out with api_key="", which SAM.gov rejects outright."""
    original = settings.sam_gov_api_key
    settings.sam_gov_api_key = ""
    try:
        scanner = SAMGovScanner()
        assert scanner._api_key == "DEMO_KEY"
    finally:
        settings.sam_gov_api_key = original


def test_uses_configured_setting_when_present():
    original = settings.sam_gov_api_key
    settings.sam_gov_api_key = "REAL_CONFIGURED_KEY"
    try:
        scanner = SAMGovScanner()
        assert scanner._api_key == "REAL_CONFIGURED_KEY"
    finally:
        settings.sam_gov_api_key = original


async def test_awards_scan_sends_posted_to_alongside_posted_from():
    """Regression test: live-confirmed HTTP 400 from SAM.gov's opportunities
    search — postedFrom is a required paired parameter with postedTo on
    that endpoint. Without postedTo, every awards scan failed outright
    ("SAM.gov awards API returned no response" was always a 400, never a
    real empty result)."""
    scanner = SAMGovScanner(api_key="TEST_KEY")
    scanner._get = AsyncMock(  # type: ignore[method-assign]
        return_value=_empty_response({"opportunitiesData": []})
    )

    await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    awards_call = scanner._get.call_args_list[1]
    params = awards_call.kwargs["params"]
    assert "postedFrom" in params
    assert "postedTo" in params


async def test_entity_scan_omits_include_sections():
    """Regression test: live-confirmed HTTP 400 from SAM.gov's entity
    search, isolated by testing this endpoint's other params individually
    against the real API — legalBusinessName, registrationStatus, and
    purposeOfRegistrationCode all work fine on their own, so
    includeSections was the only remaining suspect and turned out to be
    the cause. It's also unnecessary: the API returns entityRegistration,
    coreData, assertions, and pointsOfContact in full by default."""
    scanner = SAMGovScanner(api_key="TEST_KEY")
    scanner._get = AsyncMock(  # type: ignore[method-assign]
        return_value=_empty_response({"entityData": []})
    )

    await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    entity_call = scanner._get.call_args_list[0]
    params = entity_call.kwargs["params"]
    assert "includeSections" not in params
