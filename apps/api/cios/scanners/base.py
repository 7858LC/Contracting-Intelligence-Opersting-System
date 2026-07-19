"""Base scanner interface — all signal source adapters implement this."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


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

    def __init__(self, timeout: int = 30, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._http = httpx.AsyncClient(
            headers=_DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    async def __aenter__(self) -> "BaseScanner":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._http.aclose()

    @abstractmethod
    async def scan(self, keywords: list[str], **kwargs: Any) -> ScanResult:
        """Run a scan and return a ScanResult."""

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response | None:
        """GET with retry and rate-limit backoff."""
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self._rate_limit_delay * attempt)
                response = await self._http.get(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503):
                    wait = (2 ** attempt) * 2
                    logger.info("Rate limited by %s — waiting %ss", url, wait)
                    await asyncio.sleep(wait)
                else:
                    logger.warning("HTTP %s from %s", e.response.status_code, url)
                    return None
            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning("Request error %s: %s", url, e)
                if attempt == self.max_retries - 1:
                    return None
        return None

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response | None:
        """POST with retry."""
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self._rate_limit_delay * attempt)
                response = await self._http.post(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503):
                    await asyncio.sleep((2 ** attempt) * 2)
                else:
                    logger.warning("HTTP %s from %s", e.response.status_code, url)
                    return None
            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning("POST error %s: %s", url, e)
                if attempt == self.max_retries - 1:
                    return None
        return None
