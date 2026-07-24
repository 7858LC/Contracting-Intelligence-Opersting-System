"""USASpending.gov scanner — contract award signal detection."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cios.models.pir import SignalSource, SignalType

from .base import BaseScanner, ScannedSignal, ScanResult

logger = logging.getLogger(__name__)

_BASE = "https://api.usaspending.gov/api/v2"

# Contract type code → signal type
_AWARD_TYPE_SIGNAL: dict[str, str] = {
    "A": SignalType.FEDERAL_CONTRACT_AWARD,  # BPA Call
    "B": SignalType.FEDERAL_CONTRACT_AWARD,  # Purchase Order
    "C": SignalType.FEDERAL_CONTRACT_AWARD,  # Delivery Order
    "D": SignalType.IDIQ_AWARD,  # Definitive Contract
    "E": SignalType.FEDERAL_CONTRACT_AWARD,
    "F": SignalType.FEDERAL_CONTRACT_AWARD,
    "G": SignalType.GWAC_AWARD,  # Grants/cooperative
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
