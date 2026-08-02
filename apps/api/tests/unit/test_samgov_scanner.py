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

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock

import httpx

from cios.config import settings
from cios.scanners.samgov import SAMGovScanner


def _empty_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


def _wire_transport(
    scanner: SAMGovScanner, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Point the scanner at a fake transport, exercising the real _get path.

    Deliberately does NOT mock _get — the whole point of these diagnostics is
    what BaseScanner._request records when a real httpx call fails.
    """
    scanner._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers=scanner.default_headers,
        follow_redirects=True,
    )
    scanner.max_retries = 1
    scanner._rate_limit_delay = 0.0


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


# ── Failure diagnostics ────────────────────────────────────────────────────────
#
# Every one of these used to collapse to the single string "SAM.gov entity API
# returned no response", which is emitted identically for an HTTP 400, an HTTP
# 403, a DEMO_KEY 429, a DNS failure and a connect timeout. That message is what
# the user sees in the browser, and it was never enough to tell which of those
# had happened — every round of this investigation stalled waiting on Render
# worker logs nobody in the loop could read.


async def test_http_error_surfaces_status_code_and_body_snippet():
    scanner = SAMGovScanner(api_key="TEST_KEY_WXYZ")
    _wire_transport(
        scanner,
        lambda request: httpx.Response(
            403, text='{"error":{"code":"API_KEY_INVALID","message":"An invalid api_key"}}'
        ),
    )

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    joined = " | ".join(result.errors)
    assert "HTTP 403" in joined
    assert "API_KEY_INVALID" in joined
    assert "api.sam.gov/entity-information/v3/entities" in joined
    assert "returned no response" not in joined


async def test_transport_error_surfaces_exception_type_and_message():
    scanner = SAMGovScanner(api_key="TEST_KEY_WXYZ")

    def _boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[Errno -2] Name or service not known")

    _wire_transport(scanner, _boom)

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    joined = " | ".join(result.errors)
    assert "ConnectError" in joined
    assert "Name or service not known" in joined
    assert "returned no response" not in joined


async def test_timeout_surfaces_as_timeout_not_generic_failure():
    scanner = SAMGovScanner(api_key="TEST_KEY_WXYZ")

    def _slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    _wire_transport(scanner, _slow)

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    assert "ConnectTimeout" in " | ".join(result.errors)


async def test_error_reports_a_real_key_by_masked_tail_only():
    scanner = SAMGovScanner(api_key="sam-live-key-ABCD1234")
    _wire_transport(scanner, lambda request: httpx.Response(400, text="Bad Request"))

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    joined = " | ".join(result.errors)
    assert "...1234" in joined
    assert "21 chars" in joined
    # The key itself must never reach a persisted, browser-rendered string.
    assert "sam-live-key-ABCD1234" not in joined


async def test_error_says_so_when_running_on_the_demo_key_fallback(monkeypatch):
    """A DEMO_KEY 429 and a real-key failure are indistinguishable otherwise."""
    monkeypatch.setattr(settings, "sam_gov_api_key", "")
    scanner = SAMGovScanner()
    _wire_transport(scanner, lambda request: httpx.Response(429, text="rate limit exceeded"))
    # 429 is the retry path; don't actually sleep through the backoff.
    monkeypatch.setattr("cios.scanners.base.asyncio.sleep", AsyncMock())

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    joined = " | ".join(result.errors)
    assert "DEMO_KEY fallback" in joined
    assert "SAM_GOV_API_KEY is unset" in joined
    assert "HTTP 429" in joined


async def test_api_key_is_never_echoed_back_out_of_a_response_body():
    key = "sam-live-key-ABCD1234"
    scanner = SAMGovScanner(api_key=key)
    _wire_transport(scanner, lambda request: httpx.Response(400, text=f"bad api_key={key}"))

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    joined = " | ".join(result.errors)
    assert key not in joined
    assert "[REDACTED_API_KEY]" in joined


async def test_requests_identify_as_a_json_api_client_not_a_fake_browser():
    """api.sam.gov is a JSON API. Claiming to be Chrome from a Python client —
    with none of a browser's other headers and a Python TLS fingerprint — is
    what bot-management layers in front of federal API gateways score as an
    impersonating client, and `Accept: text/html` on a JSON endpoint invites a
    406 besides. The browser headers exist for jobs.py's HTML scraping only."""
    seen: dict[str, str] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={"entityData": []})

    scanner = SAMGovScanner(api_key="TEST_KEY")
    _wire_transport(scanner, _capture)

    await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    assert "Mozilla" not in seen["user-agent"]
    assert seen["user-agent"].startswith("CIOS-ProcurementRadar/")
    assert seen["accept"] == "application/json"
