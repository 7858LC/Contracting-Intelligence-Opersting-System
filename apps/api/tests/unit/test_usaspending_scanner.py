"""USASpendingScanner must request fields USASpending's API actually recognizes.

Regression test for a live-confirmed HTTP 400: the `fields` list requested
"recipient_uei" for the recipient's UEI, but every other entry in the same
list is Title Case matching USASpending's real field vocabulary ("Award ID",
"Recipient Name", "Awarding Agency", ...). "recipient_uei" isn't a real
field name there — the correct one is "Recipient UEI" — so every
spending_by_award call in _scan_recent_awards/_scan_recompetes 400'd
outright, which _post() surfaces as "no response", not a real empty result.
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

from cios.scanners.usaspending import USASpendingScanner


def _empty_response() -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"results": []}
    return resp


async def test_recent_awards_scan_requests_title_case_recipient_uei_field():
    scanner = USASpendingScanner()
    scanner._post = AsyncMock(return_value=_empty_response())  # type: ignore[method-assign]

    await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    for call in scanner._post.call_args_list:
        fields = call.kwargs["json"]["fields"]
        assert "recipient_uei" not in fields
        assert "Recipient UEI" in fields


def _wire_transport(
    scanner: USASpendingScanner, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Point the scanner at a fake transport, exercising the real _post path.

    Deliberately does NOT mock _post — what is under test here is what
    BaseScanner._request records when a real httpx call fails.
    """
    scanner._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers=scanner.default_headers,
        follow_redirects=True,
    )
    scanner.max_retries = 1
    scanner._rate_limit_delay = 0.0


# ── Failure diagnostics ────────────────────────────────────────────────────────
#
# USASpending needs no API key at all, so when its calls fail alongside
# SAM.gov's with the same generic "returned no response" the two look like one
# shared problem when they may well be two unrelated ones. These assert the
# error text now says which.


async def test_http_error_surfaces_status_code_and_body_snippet():
    scanner = USASpendingScanner()
    _wire_transport(
        scanner,
        lambda request: httpx.Response(
            400, text='{"detail":"Field \'Action Date\' is not a valid sort field"}'
        ),
    )

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    joined = " | ".join(result.errors)
    assert "HTTP 400" in joined
    assert "not a valid sort field" in joined
    assert "api.usaspending.gov/api/v2/search/spending_by_award/" in joined
    assert "returned no response" not in joined


async def test_transport_error_surfaces_exception_type_and_message():
    scanner = USASpendingScanner()

    def _boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("The read operation timed out")

    _wire_transport(scanner, _boom)

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    joined = " | ".join(result.errors)
    assert "ReadTimeout" in joined
    assert "read operation timed out" in joined


async def test_recompete_search_failure_is_reported_instead_of_swallowed():
    """_scan_recompetes used to `return` silently on a failed _post, hiding a
    third of this scanner's failures from the scan job's error report."""
    scanner = USASpendingScanner()
    _wire_transport(scanner, lambda request: httpx.Response(500, text="upstream error"))

    result = await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    assert any("recompete search failed" in e for e in result.errors)


async def test_requests_identify_as_a_json_api_client_not_a_fake_browser():
    """Same reasoning as the SAM.gov scanner: api.usaspending.gov is a JSON
    API, and a Chrome User-Agent from a Python client is a bot-management
    signal, not a compatibility measure."""
    seen: dict[str, str] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={"results": []})

    scanner = USASpendingScanner()
    _wire_transport(scanner, _capture)

    await scanner.scan(keywords=["Leidos"], naics_codes=[], days_back=30)

    assert "Mozilla" not in seen["user-agent"]
    assert seen["user-agent"].startswith("CIOS-ProcurementRadar/")
    assert seen["accept"] == "application/json"
