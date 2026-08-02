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
