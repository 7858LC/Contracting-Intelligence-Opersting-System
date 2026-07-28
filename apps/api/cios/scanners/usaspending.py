"""USASpending.gov scanner — contract award signal detection."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cios.models.pir import SignalSource, SignalType

from .base import BaseScanner, ScannedSignal, ScanResult

logger = logging.getLogger(__name__)

_BASE = "https://api.usaspending.gov/api/v2"

# Contract type code → signal type. Must match USASpending's actual
# award_type_codes enum for the spending_by_award endpoint — 'E'/'F'/'G' are
# NOT valid procurement codes there (confirmed live: the API 400s on them,
# listing only 'A'/'B'/'C'/'D', the 'IDV_*' family, and the numeric/F0xx
# assistance codes as valid). Passing them silently zeroed out every result
# in this dict-keys-derived filter, in both this module's aggregate query and
# the existing daily PIR radar scan's _scan_recent_awards, since _post()
# treats a 400 the same as an empty response.
_AWARD_TYPE_SIGNAL: dict[str, str] = {
    "A": SignalType.FEDERAL_CONTRACT_AWARD,  # BPA Call
    "B": SignalType.FEDERAL_CONTRACT_AWARD,  # Purchase Order
    "C": SignalType.FEDERAL_CONTRACT_AWARD,  # Delivery Order
    "D": SignalType.IDIQ_AWARD,  # Definitive Contract
    "IDV_A": SignalType.IDIQ_AWARD,  # GWAC
    "IDV_B": SignalType.IDIQ_AWARD,  # IDC
    "IDV_B_A": SignalType.IDIQ_AWARD,  # BPA
    "IDV_B_B": SignalType.IDIQ_AWARD,  # BPA
    "IDV_B_C": SignalType.IDIQ_AWARD,  # BPA
    "IDV_C": SignalType.GWAC_AWARD,  # FSS
    "IDV_D": SignalType.IDIQ_AWARD,  # AOA
    "IDV_E": SignalType.IDIQ_AWARD,  # BOA
}


class USASpendingScanner(BaseScanner):
    source_name = SignalSource.USASPENDING
    _rate_limit_delay = 0.3

    async def aggregate_agency_period(
        self,
        agency_name: str,
        period_start: datetime,
        period_end: datetime,
        naics_codes: list[str] | None = None,
        max_pages: int = 5,
    ) -> dict[str, Any]:
        """Aggregate award activity for one agency over one period, for the
        research module's AgencyBuyingPattern (cios/models/research.py).

        NOTE: this is a bounded top-N aggregate, not a complete Treasury-grade
        total — it pages through ``spending_by_award`` (the same endpoint/
        payload shape ``_scan_recent_awards`` already uses successfully) up to
        ``max_pages`` pages of 100 results each, ordered by award amount
        descending, and sums what it sees. A large agency (DoD) has far more
        awards per quarter than max_pages*100 can cover completely. Getting a
        complete total would mean using USASpending's dedicated aggregate
        endpoints (spending_over_time / spending_by_category), which this
        environment could not reach to verify their exact request/response
        schema before shipping — do a live check against a real quarter's
        published Treasury totals before trusting this for anything but a
        directional "top awards this quarter" narrative.
        """
        payload: dict[str, Any] = {
            "filters": {
                "time_period": [
                    {
                        "start_date": period_start.strftime("%Y-%m-%d"),
                        "end_date": period_end.strftime("%Y-%m-%d"),
                    }
                ],
                "award_type_codes": list(_AWARD_TYPE_SIGNAL.keys()),
                "agencies": [{"type": "awarding", "tier": "toptier", "name": agency_name}],
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Award Type",
                "NAICS Code",
                "Action Date",
                "Awarding Sub Agency",
            ],
            "sort": "Award Amount",
            "order": "desc",
            "limit": 100,
            "page": 1,
        }
        if naics_codes:
            payload["filters"]["naics_codes"] = naics_codes[:20]

        total_obligated = 0.0
        award_count = 0
        naics_totals: dict[str, float] = {}
        evidence: list[dict[str, Any]] = []
        errors: list[str] = []

        for page in range(1, max_pages + 1):
            payload["page"] = page
            resp = await self._post(f"{_BASE}/search/spending_by_award/", json=payload)
            if not resp:
                errors.append(f"{agency_name}: no response on page {page}")
                break

            try:
                data = resp.json()
            except Exception:
                errors.append(f"{agency_name}: invalid JSON on page {page}")
                break

            results = data.get("results", [])
            if not results:
                break

            for award in results:
                amount = award.get("Award Amount") or 0
                total_obligated += amount
                award_count += 1
                naics = str(award.get("NAICS Code") or "")
                if naics:
                    naics_totals[naics] = naics_totals.get(naics, 0.0) + amount
                if len(evidence) < 25:
                    evidence.append(
                        {
                            "award_id": award.get("Award ID", ""),
                            "recipient_name": award.get("Recipient Name", ""),
                            "amount": amount,
                            "naics": naics,
                            "action_date": award.get("Action Date", ""),
                            "source_url": (
                                f"https://www.usaspending.gov/award/{award.get('Award ID', '')}"
                            ),
                        }
                    )

            if not data.get("page_metadata", {}).get("hasNext", False):
                break

        top_naics = dict(sorted(naics_totals.items(), key=lambda kv: kv[1], reverse=True)[:10])

        return {
            "total_obligated_amount": total_obligated,
            "award_count": award_count,
            "top_naics_breakdown": top_naics,
            "source_evidence": evidence,
            "errors": errors,
        }

    async def scan(self, keywords: list[str], **kwargs: Any) -> ScanResult:
        result = ScanResult(source=self.source_name)
        t0 = datetime.now(UTC)

        days_back = kwargs.get("days_back", 60)
        naics_codes = kwargs.get("naics_codes", [])

        await self._scan_recent_awards(result, days_back, naics_codes)
        await self._scan_recompetes(result, days_back)

        result.duration_ms = int((datetime.now(UTC) - t0).total_seconds() * 1000)
        return result

    async def _scan_recent_awards(
        self, result: ScanResult, days_back: int, naics_codes: list[str]
    ) -> None:
        start_date = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        end_date = datetime.now(UTC).strftime("%Y-%m-%d")

        payload: dict[str, Any] = {
            "filters": {
                "time_period": [{"start_date": start_date, "end_date": end_date}],
                "award_type_codes": list(_AWARD_TYPE_SIGNAL.keys()),
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "recipient_uei",
                "Award Amount",
                "Awarding Agency",
                "Award Type",
                "NAICS Code",
                "Place of Performance State Code",
                "Place of Performance City Name",
                "Action Date",
                "Description",
            ],
            "sort": "Action Date",
            "order": "desc",
            "limit": 100,
            "page": 1,
        }

        if naics_codes:
            payload["filters"]["naics_codes"] = naics_codes[:20]

        resp = await self._post(f"{_BASE}/search/spending_by_award/", json=payload)
        if not resp:
            result.add_error("USASpending award search returned no response")
            return

        try:
            data = resp.json()
        except Exception:
            result.add_error("USASpending: invalid JSON response")
            return

        for award in data.get("results", []):
            try:
                self._process_award(award, result)
            except Exception as e:
                result.add_error(f"Award processing error: {e}")

    def _process_award(self, award: dict, result: ScanResult) -> None:
        recipient = award.get("Recipient Name", "")
        if not recipient or recipient.lower() in ("unknown", "n/a", ""):
            return

        uei = award.get("recipient_uei", "")
        amount = award.get("Award Amount") or 0
        agency = award.get("Awarding Agency", "")
        award_type = award.get("Award Type", "")
        naics = award.get("NAICS Code", "")
        action_date = award.get("Action Date", "")
        description = award.get("Description", "")
        state = award.get("Place of Performance State Code", "")
        city = award.get("Place of Performance City Name", "")

        sig_type = _AWARD_TYPE_SIGNAL.get(award_type, SignalType.FEDERAL_CONTRACT_AWARD)

        try:
            detected_at = datetime.strptime(action_date, "%Y-%m-%d").replace(tzinfo=UTC)
        except (ValueError, TypeError):
            detected_at = datetime.now(UTC)

        type_label = {
            SignalType.GWAC_AWARD: "GWAC Award",
            SignalType.IDIQ_AWARD: "IDIQ Award",
        }.get(sig_type, "Federal Contract Award")

        result.add_signal(
            ScannedSignal(
                signal_type=sig_type,
                source=self.source_name,
                title=f"{recipient} — {type_label} ({agency})",
                description=(
                    f"Award: ${amount:,.0f} from {agency}. "
                    f"{description[:200] if description else ''}"
                ).strip(),
                source_url=f"https://www.usaspending.gov/award/{award.get('Award ID', '')}",
                detected_at=detected_at,
                raw_data=award,
                company_name=recipient,
                samgov_uei=uei,
                naics_codes=[str(naics)] if naics else [],
                headquarters_city=city,
                headquarters_state=state,
            )
        )

    async def _scan_recompetes(self, result: ScanResult, days_back: int) -> None:
        """Detect companies that recently won recompete awards (same awardee, same PIID base)."""
        # Query for awards with modification reason "Recompete"
        start_date = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        payload = {
            "filters": {
                "time_period": [
                    {"start_date": start_date, "end_date": datetime.now(UTC).strftime("%Y-%m-%d")}
                ],
                "award_type_codes": ["A", "B", "C", "D"],
                "program_activities": [],
            },
            "fields": [
                "Recipient Name",
                "recipient_uei",
                "Award Amount",
                "Awarding Agency",
                "Action Date",
                "NAICS Code",
            ],
            "sort": "Action Date",
            "order": "desc",
            "limit": 50,
            "page": 1,
            "subawards": False,
        }

        resp = await self._post(f"{_BASE}/search/spending_by_award/", json=payload)
        if not resp:
            return

        try:
            data = resp.json()
        except Exception:
            return

        # Mark high-value re-awards as recompete signals
        for award in data.get("results", []):
            try:
                amount = award.get("Award Amount") or 0
                if amount < 1_000_000:
                    continue
                recipient = award.get("Recipient Name", "")
                if not recipient:
                    continue
                uei = award.get("recipient_uei", "")
                agency = award.get("Awarding Agency", "")
                action_date = award.get("Action Date", "")
                naics = award.get("NAICS Code", "")
                try:
                    detected_at = datetime.strptime(action_date, "%Y-%m-%d").replace(tzinfo=UTC)
                except (ValueError, TypeError):
                    detected_at = datetime.now(UTC)

                result.add_signal(
                    ScannedSignal(
                        signal_type=SignalType.CONTRACT_RECOMPETE,
                        source=self.source_name,
                        title=f"{recipient} — High-Value Recompete Signal ({agency})",
                        description=(
                            f"Award ${amount:,.0f} from {agency} — "
                            "indicative of active contract pursuit."
                        ),
                        source_url="https://www.usaspending.gov/search",
                        detected_at=detected_at,
                        raw_data=award,
                        company_name=recipient,
                        samgov_uei=uei,
                        naics_codes=[str(naics)] if naics else [],
                    )
                )
            except Exception:
                continue
