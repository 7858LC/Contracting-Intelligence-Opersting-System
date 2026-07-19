"""Job board scanner — detects GovCon hiring signals via Playwright."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from cios.models.pir import SignalSource, SignalType
from .base import BaseScanner, ScannedSignal, ScanResult

logger = logging.getLogger(__name__)

# Keyword → signal type mapping
JOB_SIGNAL_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bcapture\s+manager\b", re.I), SignalType.HIRING_CAPTURE_MANAGER),
    (re.compile(r"\bproposal\s+manager\b", re.I), SignalType.HIRING_PROPOSAL_MANAGER),
    (re.compile(r"\bproposals?\s+coordinator\b", re.I), SignalType.HIRING_PROPOSAL_MANAGER),
    (re.compile(r"\bbd\s+director\b|\bbusiness\s+development\s+director\b", re.I), SignalType.HIRING_BD_DIRECTOR),
    (re.compile(r"\bvp\s+(of\s+)?business\s+development\b", re.I), SignalType.HIRING_BD_DIRECTOR),
    (re.compile(r"\bcontracts\s+manager\b|\bcontracts\s+specialist\b", re.I), SignalType.HIRING_CONTRACTS_MANAGER),
    (re.compile(r"\bpricing\s+manager\b|\bpricing\s+analyst\b|\bcost\s+\/\s*price\b", re.I), SignalType.HIRING_PRICING_MANAGER),
    (re.compile(r"\bcompliance\s+manager\b|\bcmmc\s+compliance\b", re.I), SignalType.HIRING_COMPLIANCE_MANAGER),
    (re.compile(r"\bgovernment\s+(sales|account)\s+manager\b", re.I), SignalType.HIRING_GOVERNMENT_SALES),
    (re.compile(r"\bfederal\s+sales\b", re.I), SignalType.HIRING_GOVERNMENT_SALES),
    (re.compile(r"\bprogram\s+manager\b", re.I), SignalType.HIRING_PROGRAM_MANAGER),
    (re.compile(r"\bsecret\b|\bts\/sci\b|\bactive\s+clearance\b|\bsci\s+eligible\b", re.I), SignalType.HIRING_CLEARED_PERSONNEL),
]


def _classify_job(title: str) -> str | None:
    for pattern, sig_type in JOB_SIGNAL_MAP:
        if pattern.search(title):
            return sig_type
    return None


def _extract_company_domain(company_name: str) -> str | None:
    """Best-effort domain guess from company name."""
    clean = re.sub(r"[^a-z0-9\s]", "", company_name.lower())
    words = clean.split()
    if not words:
        return None
    stop = {"inc", "llc", "corp", "the", "and", "of", "group", "company", "co", "ltd"}
    sig = [w for w in words if w not in stop]
    if sig:
        return f"{sig[0]}.com"
    return None


class JobBoardScanner(BaseScanner):
    """Scans job boards for GovCon-relevant hiring signals using Playwright."""

    source_name = "job_boards"
    _rate_limit_delay = 2.0

    async def scan(self, keywords: list[str], **kwargs: Any) -> ScanResult:
        result = ScanResult(source=self.source_name)
        t0 = datetime.now(UTC)

        # Run Indeed and ClearanceJobs in parallel; LinkedIn last (stricter)
        tasks = [
            self._scan_indeed(result, keywords),
            self._scan_clearancejobs(result, keywords),
            self._scan_ziprecruiter(result, keywords),
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        # LinkedIn is sensitive — sequential and respectful
        await self._scan_linkedin_public(result, keywords)

        result.duration_ms = int((datetime.now(UTC) - t0).total_seconds() * 1000)
        return result

    # ── Indeed ─────────────────────────────────────────────────────────────────

    async def _scan_indeed(self, result: ScanResult, keywords: list[str]) -> None:
        for keyword in keywords[:5]:  # cap to avoid hammering
            await self._fetch_indeed_jobs(result, keyword)
            await asyncio.sleep(self._rate_limit_delay)

    async def _fetch_indeed_jobs(self, result: ScanResult, keyword: str) -> None:
        url = "https://www.indeed.com/jobs"
        params = {"q": keyword, "l": "United States", "sort": "date", "fromage": "14"}

        resp = await self._get(url, params=params)
        if not resp:
            result.add_error(f"Indeed: no response for '{keyword}'")
            return

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
        except ImportError:
            result.add_error("Indeed scraping requires beautifulsoup4")
            return

        for card in soup.select("div.job_seen_beacon, div.jobsearch-SerpJobCard"):
            try:
                title_el = card.select_one("h2.jobTitle span, a.jobtitle")
                company_el = card.select_one("span.companyName, span.company")
                location_el = card.select_one("div.companyLocation")
                link_el = card.select_one("a[href*='/rc/clk'], a.jobtitle")

                if not (title_el and company_el):
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True)
                location = location_el.get_text(strip=True) if location_el else ""
                href = link_el["href"] if link_el and link_el.get("href") else ""
                source_url = f"https://www.indeed.com{href}" if href.startswith("/") else href

                sig_type = _classify_job(title)
                if not sig_type:
                    continue

                state = _extract_state(location)
                city = _extract_city(location)

                result.add_signal(ScannedSignal(
                    signal_type=sig_type,
                    source=SignalSource.INDEED,
                    title=f"{company} — Hiring: {title}",
                    description=f"Active job posting on Indeed: {title} in {location}",
                    source_url=source_url,
                    detected_at=datetime.now(UTC),
                    raw_data={"title": title, "company": company, "location": location, "keyword": keyword},
                    company_name=company,
                    company_domain=_extract_company_domain(company),
                    headquarters_city=city,
                    headquarters_state=state,
                ))
            except Exception:
                continue

    # ── ClearanceJobs ──────────────────────────────────────────────────────────

    async def _scan_clearancejobs(self, result: ScanResult, keywords: list[str]) -> None:
        for keyword in keywords[:5]:
            await self._fetch_clearancejobs(result, keyword)
            await asyncio.sleep(self._rate_limit_delay)

    async def _fetch_clearancejobs(self, result: ScanResult, keyword: str) -> None:
        url = "https://www.clearancejobs.com/jobs"
        params = {"query": keyword, "radius": "50", "country": "us"}

        resp = await self._get(url, params=params)
        if not resp:
            return

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
        except ImportError:
            return

        for card in soup.select("div[data-testid='job-card'], article.job-listing"):
            try:
                title_el = card.select_one("h2, h3, a.job-title")
                company_el = card.select_one("span.company-name, div.company")
                location_el = card.select_one("span.location, div.location")

                if not (title_el and company_el):
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True)
                location = location_el.get_text(strip=True) if location_el else ""

                sig_type = _classify_job(title) or SignalType.HIRING_CLEARED_PERSONNEL

                result.add_signal(ScannedSignal(
                    signal_type=sig_type,
                    source=SignalSource.CLEARANCEJOBS,
                    title=f"{company} — Cleared Hire: {title}",
                    description=f"Cleared position on ClearanceJobs: {title} ({location})",
                    source_url=f"https://www.clearancejobs.com/jobs?query={keyword}",
                    detected_at=datetime.now(UTC),
                    raw_data={"title": title, "company": company, "location": location},
                    company_name=company,
                    company_domain=_extract_company_domain(company),
                    headquarters_state=_extract_state(location),
                ))
            except Exception:
                continue

    # ── ZipRecruiter ───────────────────────────────────────────────────────────

    async def _scan_ziprecruiter(self, result: ScanResult, keywords: list[str]) -> None:
        for keyword in keywords[:4]:
            url = "https://www.ziprecruiter.com/candidate/search"
            params = {"search": keyword, "location": "United States", "days": "14"}

            resp = await self._get(url, params=params)
            if not resp:
                continue

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
            except ImportError:
                break

            for card in soup.select("article.job_content, div[data-entity-type='job']"):
                try:
                    title_el = card.select_one("h2 a, a.job_link")
                    company_el = card.select_one("a[data-testid='company-name'], span.hiring_company_text")
                    location_el = card.select_one("span[data-testid='job-location'], .location_text")

                    if not (title_el and company_el):
                        continue

                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True)
                    location = location_el.get_text(strip=True) if location_el else ""
                    href = title_el.get("href", "")

                    sig_type = _classify_job(title)
                    if not sig_type:
                        continue

                    result.add_signal(ScannedSignal(
                        signal_type=sig_type,
                        source=SignalSource.ZIPRECRUITER,
                        title=f"{company} — Hiring: {title}",
                        description=f"Job posting on ZipRecruiter: {title} in {location}",
                        source_url=href if href.startswith("http") else f"https://www.ziprecruiter.com{href}",
                        detected_at=datetime.now(UTC),
                        raw_data={"title": title, "company": company, "location": location, "keyword": keyword},
                        company_name=company,
                        company_domain=_extract_company_domain(company),
                        headquarters_state=_extract_state(location),
                    ))
                except Exception:
                    continue

            await asyncio.sleep(self._rate_limit_delay)

    # ── LinkedIn public job search ─────────────────────────────────────────────

    async def _scan_linkedin_public(self, result: ScanResult, keywords: list[str]) -> None:
        """Use LinkedIn's unauthenticated job listing API (public endpoint)."""
        for keyword in keywords[:3]:
            url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            params = {
                "keywords": keyword,
                "location": "United States",
                "geoId": "103644278",
                "trk": "public_jobs_jobs-search-bar_search-submit",
                "start": 0,
            }

            resp = await self._get(url, params=params, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,*/*",
                "Referer": "https://www.linkedin.com/jobs/search/",
            })

            if not resp:
                result.add_error(f"LinkedIn: no response for '{keyword}'")
                await asyncio.sleep(5)
                continue

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
            except ImportError:
                result.add_error("LinkedIn scraping requires beautifulsoup4")
                return

            for card in soup.select("li, div.base-card"):
                try:
                    title_el = card.select_one("h3.base-search-card__title, span.sr-only")
                    company_el = card.select_one("h4.base-search-card__subtitle a, a.hidden-nested-link")
                    location_el = card.select_one("span.job-search-card__location")
                    link_el = card.select_one("a.base-card__full-link, a[data-tracking-control-name]")

                    if not (title_el and company_el):
                        continue

                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True)
                    location = location_el.get_text(strip=True) if location_el else ""
                    source_url = link_el["href"] if link_el and link_el.get("href") else ""

                    sig_type = _classify_job(title)
                    if not sig_type:
                        continue

                    result.add_signal(ScannedSignal(
                        signal_type=sig_type,
                        source=SignalSource.LINKEDIN,
                        title=f"{company} — Hiring: {title}",
                        description=f"Active job posting on LinkedIn: {title} in {location}",
                        source_url=source_url,
                        detected_at=datetime.now(UTC),
                        raw_data={"title": title, "company": company, "location": location, "keyword": keyword},
                        company_name=company,
                        company_domain=_extract_company_domain(company),
                        headquarters_state=_extract_state(location),
                    ))
                except Exception:
                    continue

            await asyncio.sleep(self._rate_limit_delay * 2)


# ── Helpers ────────────────────────────────────────────────────────────────────

_US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}

def _extract_state(location: str) -> str | None:
    parts = [p.strip() for p in location.replace(",", " ").split()]
    for part in reversed(parts):
        if part.upper() in _US_STATES:
            return part.upper()
    return None

def _extract_city(location: str) -> str | None:
    parts = [p.strip() for p in location.split(",")]
    return parts[0].strip() if parts else None
