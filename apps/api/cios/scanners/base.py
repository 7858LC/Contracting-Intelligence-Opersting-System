"""Base scanner interface — all signal source adapters implement this."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

# Browser-shaped headers. These exist for the HTML-scraping scanner
# (cios/scanners/jobs.py), which fetches ordinary web pages and needs to look
# like a browser to get served markup at all.
#
# Do NOT use these for a JSON API. Claiming to be Chrome while presenting a
# Python TLS fingerprint and none of a real browser's other headers is exactly
# the shape WAF/bot-management layers in front of federal API gateways score as
# an impersonating bot, and `Accept: text/html` on a JSON endpoint invites a
# 406 on top of that. JSON API scanners use _JSON_API_HEADERS below.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# api.sam.gov and api.usaspending.gov are documented public JSON APIs consumed
# with a real API key (SAM) or anonymously (USASpending). Identify honestly and
# ask for JSON — that is what these APIs expect, and it removes the
# browser-impersonation signal described above from the request entirely.
_JSON_API_HEADERS = {
    "User-Agent": "CIOS-ProcurementRadar/1.0 (+https://cios.ai)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

# Back-compat alias — some callers/tests referenced the old name.
_DEFAULT_HEADERS = _BROWSER_HEADERS

# How much of a failing response body to keep in a user-visible diagnostic.
# Long enough for SAM.gov/USASpending's actual error text, short enough that
# five of these still fit inside PIRScanJob.error_message's 2000-char budget.
_BODY_SNIPPET_CHARS = 160


def _safe_url(url: str) -> str:
    """Host + path only.

    Diagnostics built from this end up in PIRScanJob.error_message and are
    rendered straight into the browser, and SAM.gov takes its API key as a
    *query parameter* — so the query string must never make it into one.
    """
    parts = urlsplit(url)
    return f"{parts.netloc}{parts.path}" or url


def _body_snippet(response: httpx.Response) -> str:
    """First few hundred characters of a failing response body, whitespace-collapsed."""
    try:
        text = response.text
    except Exception:  # pragma: no cover - undecodable body
        return ""
    text = " ".join(text.split())
    if len(text) > _BODY_SNIPPET_CHARS:
        text = text[:_BODY_SNIPPET_CHARS] + "..."
    return text


@dataclass
class RequestFailure:
    """Why a _get/_post call could not produce a usable response.

    Exists because collapsing every failure mode to ``None`` made an HTTP 400,
    an HTTP 403, a DEMO_KEY 429, a DNS failure, and a connect timeout all
    indistinguishable from each other and from a genuinely empty result — the
    caller could only ever report "returned no response", which is true of all
    of them and diagnostic of none of them.
    """

    url: str
    method: str
    attempts: int
    status_code: int | None = None
    exception_type: str | None = None
    message: str = ""
    body_snippet: str = ""

    def describe(self) -> str:
        plural = "attempt" if self.attempts == 1 else "attempts"
        where = f"{self.method} {self.url} after {self.attempts} {plural}"
        if self.status_code is not None:
            out = f"HTTP {self.status_code} from {where}"
            if self.body_snippet:
                out = f"{out} - body: {self.body_snippet}"
            return out
        detail = self.message or "(no detail)"
        return f"{self.exception_type or 'UnknownError'} on {where} - {detail}"


@dataclass
class ScannedSignal:
    signal_type: str
    source: str
    title: str
    description: str | None
    source_url: str | None
    detected_at: datetime
    raw_data: dict[str, Any] = field(default_factory=dict)
    company_name: str = ""
    company_domain: str | None = None
    company_website: str | None = None
    company_linkedin: str | None = None
    samgov_uei: str | None = None
    naics_codes: list[str] = field(default_factory=list)
    headquarters_city: str | None = None
    headquarters_state: str | None = None
    employee_count_range: str | None = None
    set_aside_types: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    source: str
    signals: list[ScannedSignal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    companies_found: int = 0
    duration_ms: int = 0

    def add_signal(self, signal: ScannedSignal) -> None:
        self.signals.append(signal)
        self.companies_found = len({s.company_name for s in self.signals if s.company_name})

    def add_error(self, msg: str) -> None:
        logger.warning("Scanner[%s] error: %s", self.source, msg)
        self.errors.append(msg)


class BaseScanner(ABC):
    """All signal source scanners extend this."""

    source_name: str = "unknown"
    _rate_limit_delay: float = 1.0  # seconds between requests
    #: Headers this scanner's HTTP client sends. HTML-scraping scanners keep
    #: the browser-shaped defaults; JSON API scanners override with
    #: _JSON_API_HEADERS (see samgov.py / usaspending.py).
    default_headers: dict[str, str] = _BROWSER_HEADERS

    def __init__(self, timeout: int = 30, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        # Diagnostic for the most recent failed _get/_post, cleared on success.
        # Requests inside a single scan() run strictly sequentially (never
        # gathered), so when a caller sees None this is always that call's own
        # failure.
        self.last_failure: RequestFailure | None = None
        self._http = httpx.AsyncClient(
            headers=self.default_headers,
            timeout=timeout,
            follow_redirects=True,
        )

    async def __aenter__(self) -> BaseScanner:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._http.aclose()

    @abstractmethod
    async def scan(self, keywords: list[str], **kwargs: Any) -> ScanResult:
        """Run a scan and return a ScanResult."""

    def _redact(self, text: str) -> str:
        """Hook for subclasses to strip their own secrets out of diagnostics.

        Diagnostics are persisted and shown to end users, so anything a
        subclass authenticates with (SAM.gov's ``api_key``) must be scrubbed
        before it can be echoed back out of a response body.
        """
        return text

    def failure_detail(self) -> str:
        """Human-readable reason the last _get/_post returned None.

        Callers put this straight into ``ScanResult.add_error`` so the real
        cause (status code + body, or exception type + message) reaches the
        user's screen instead of a generic "returned no response".
        """
        if self.last_failure is None:
            return "no response, and no HTTP status or transport error was recorded"
        return self.last_failure.describe()

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response | None:
        """Issue one request with retry + rate-limit backoff.

        On failure returns None *and* records why on ``self.last_failure``;
        render it with ``failure_detail()``.
        """
        failure: RequestFailure | None = None
        safe_url = _safe_url(url)

        for attempt in range(self.max_retries):
            attempts = attempt + 1
            try:
                await asyncio.sleep(self._rate_limit_delay * attempt)
                response = await self._http.request(method, url, **kwargs)
                response.raise_for_status()
                self.last_failure = None
                return response
            except httpx.HTTPStatusError as e:
                failure = RequestFailure(
                    url=safe_url,
                    method=method,
                    attempts=attempts,
                    status_code=e.response.status_code,
                    body_snippet=self._redact(_body_snippet(e.response)),
                )
                if e.response.status_code in (429, 503):
                    wait = (2**attempt) * 2
                    logger.info("Rate limited by %s — waiting %ss", safe_url, wait)
                    await asyncio.sleep(wait)
                    continue
                logger.warning("HTTP %s from %s", e.response.status_code, safe_url)
                break
            except (httpx.RequestError, httpx.TimeoutException) as e:
                failure = RequestFailure(
                    url=safe_url,
                    method=method,
                    attempts=attempts,
                    exception_type=type(e).__name__,
                    message=self._redact(str(e))[:200],
                )
                logger.warning("%s error %s: %s", method, safe_url, e)
                continue
            except Exception as e:
                # Anything else (a raw ssl.SSLError, an httpcore leak, a
                # transport bug) must not surface as an indistinguishable
                # "no response" either — record the class name and stop.
                failure = RequestFailure(
                    url=safe_url,
                    method=method,
                    attempts=attempts,
                    exception_type=type(e).__name__,
                    message=self._redact(str(e))[:200],
                )
                logger.warning("%s unexpected error %s: %r", method, safe_url, e)
                break

        self.last_failure = failure
        return None

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response | None:
        """GET with retry and rate-limit backoff. See ``_request``."""
        return await self._request("GET", url, **kwargs)

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response | None:
        """POST with retry. See ``_request``."""
        return await self._request("POST", url, **kwargs)
