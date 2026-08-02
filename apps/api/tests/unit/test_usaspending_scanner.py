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

from unittest.mock import AsyncMock, MagicMock

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
