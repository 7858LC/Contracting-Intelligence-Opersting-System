"""SAM.gov scanner — Entity Management API + Opportunities API."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cios.config import settings
from cios.models.pir import SignalSource, SignalType
from .base import BaseScanner, ScannedSignal, ScanResult

logger = logging.getLogger(__name__)

_ENTITY_API = "https://api.sam.gov/entity-information/v3/entities"
_AWARDS_API = "https://api.sam.gov/opportunities/v2/search"

# SAM.gov small business set-aside program codes → signal types
_SETASIDE_SIGNAL: dict[str, str] = {
    "SBA": SignalType.CERTIFICATION_8A,
    "8A": SignalType.CERTIFICATION_8A,
    "SDVOSBC": SignalType.CERTIFICATION_SDVOSB,
    "SDVOSBS": SignalType.CERTIFICATION_SDVOSB,
    "HZC": SignalType.CERTIFICATION_HUBZONE,
    "HZS": SignalType.CERTIFICATION_HUBZONE,
    "WOSB": SignalType.CERTIFICATION_WOSB,
    "EDWOSB": SignalType.CERTIFICATION_WOSB,
}


def _extract_setasides(entity: dict) -> list[str]:
    """Return list of set-aside types from SAM entity data."""
    codes: list[str] = []
    assertions = entity.get("assertions", {})
    sb_info = assertions.get("smallBusinessInfo", {})
    sba_cert = sb_info.get("sbaCertifications", [])
    if isinstance(sba_cert, list):
        codes.extend(sba_cert)
    return [c for c in codes if c in _SETASIDE_SIGNAL]


def _naics_from_entity(entity: dict) -> list[str]:
    codes = []
    naics_list = entity.get("assertions", {}).get("goodsAndServices", {}).get("naicsList", [])
    if isinstance(naics_list, list):
        for item in naics_list:
            code = item.get("naicsCode")
            if code:
                codes.append(str(code))
    return codes


class SAMGovScanner(BaseScanner):
    source_name = SignalSource.SAMGOV
    _rate_limit_delay = 0.5

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._api_key = api_key or getattr(settings, "sam_gov_api_key", "DEMO_KEY")

    async def scan(self, keywords: list[str], **kwargs: Any) -> ScanResult:
        result = ScanResult(source=self.source_name)
        t0 = datetime.now(UTC)

        # 1. Scan for recently registered / updated entities matching target NAICS codes
        naics_filter = kwargs.get("naics_codes", [])
        await self._scan_entities(result, naics_filter)

        # 2. Scan recent contract awards for signals
        days_back = kwargs.get("days_back", 30)
        await self._scan_awards(result, days_back)

        result.duration_ms = int((datetime.now(UTC) - t0).total_seconds() * 1000)
        return result

    async def _scan_entities(self, result: ScanResult, naics_codes: list[str]) -> None:
        """Pull entities registered or updated in the last 30 days."""
        params: dict[str, Any] = {
            "api_key": self._api_key,
            "registrationStatus": "A",
            "purposeOfRegistrationCode": "Z2",  # All awards
            "includeSections": "entityRegistration,assertions,pointsOfContact",
            "page": 0,
            "size": 100,
        }
        if naics_codes:
            params["naicsCode"] = ",".join(naics_codes[:10])

        resp = await self._get(_ENTITY_API, params=params)
        if not resp:
            result.add_error("SAM.gov entity API returned no response")
            return

        try:
            data = resp.json()
        except Exception:
            result.add_error("SAM.gov entity API: invalid JSON")
            return

        entities = data.get("entityData", [])
        for entity in entities:
            try:
                self._process_entity(entity, result)
            except Exception as e:
                result.add_error(f"Entity processing error: {e}")

    def _process_entity(self, entity: dict, result: ScanResult) -> None:
        reg = entity.get("entityRegistration", {})
        name = reg.get("legalBusinessName", "")
        if not name:
            return

        uei = reg.get("ueiSAM", "")
        cage = reg.get("cageCode", "")
        address = reg.get("physicalAddress", {})
        city = address.get("city", "")
        state = address.get("stateOrProvinceCode", "")

        naics = _naics_from_entity(entity)
        setasides = _extract_setasides(entity)

        activation = reg.get("activationDate", "")
        detected_at = _parse_sam_date(activation) or datetime.now(UTC)

        # Base SAM registration signal
        result.add_signal(ScannedSignal(
            signal_type=SignalType.SAM_REGISTRATION,
            source=self.source_name,
            title=f"{name} — SAM.gov Active Registration",
            description=f"Entity registered/active in SAM.gov: UEI {uei}, CAGE {cage}",
            source_url=f"https://sam.gov/entity/{uei}/core",
            detected_at=detected_at,
            raw_data={"uei": uei, "cage": cage, "registration": reg},
            company_name=name,
            samgov_uei=uei,
            naics_codes=naics,
            headquarters_city=city,
            headquarters_state=state,
            set_aside_types=setasides,
        ))

        # Emit a signal per set-aside certification
        for code in setasides:
            sig_type = _SETASIDE_SIGNAL.get(code, SignalType.SAM_REGISTRATION)
            result.add_signal(ScannedSignal(
                signal_type=sig_type,
                source=self.source_name,
                title=f"{name} — {code} Certification",
                description=f"Small business certification on SAM.gov: {code}",
                source_url=f"https://sam.gov/entity/{uei}/core",
                detected_at=detected_at,
                raw_data={"certification_code": code, "uei": uei},
                company_name=name,
                samgov_uei=uei,
                naics_codes=naics,
                headquarters_city=city,
                headquarters_state=state,
                set_aside_types=setasides,
            ))

    async def _scan_awards(self, result: ScanResult, days_back: int) -> None:
        """Pull recent contract awards from SAM.gov opportunities API."""
        since = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%m/%d/%Y")
        params = {
            "api_key": self._api_key,
            "typeOfSetAsideDescription": "",
            "postedFrom": since,
            "limit": 100,
            "offset": 0,
            "status": "active",
        }

        resp = await self._get(_AWARDS_API, params=params)
        if not resp:
            result.add_error("SAM.gov awards API returned no response")
            return

        try:
            data = resp.json()
        except Exception:
            result.add_error("SAM.gov awards API: invalid JSON")
            return

        for opp in data.get("opportunitiesData", []):
            try:
                self._process_award(opp, result)
            except Exception as e:
                result.add_error(f"Award processing error: {e}")

    def _process_award(self, opp: dict, result: ScanResult) -> None:
        awardee = opp.get("award", {})
        awardee_name = awardee.get("awardee", {}).get("name", "")
        if not awardee_name:
            return

        uei = awardee.get("awardee", {}).get("ueiSAM", "")
        amount = awardee.get("amount", 0)
        title = opp.get("title", "")
        opp_id = opp.get("noticeId", "")
        naics = [str(opp.get("naicsCode", ""))] if opp.get("naicsCode") else []

        # Determine signal type from opportunity type
        opp_type = opp.get("type", "").lower()
        if "idiq" in opp_type or "indefinite" in title.lower():
            sig_type = SignalType.IDIQ_AWARD
        elif "sbir" in title.lower() or "sttr" in title.lower():
            sig_type = SignalType.SBIR_STTR_AWARD
        else:
            sig_type = SignalType.FEDERAL_CONTRACT_AWARD

        posted = opp.get("postedDate", "")
        detected_at = _parse_sam_date(posted) or datetime.now(UTC)

        result.add_signal(ScannedSignal(
            signal_type=sig_type,
            source=self.source_name,
            title=f"{awardee_name} — Federal Contract Award: {title[:100]}",
            description=f"Award value: ${amount:,.0f}. Opportunity: {title[:200]}",
            source_url=f"https://sam.gov/opp/{opp_id}/view",
            detected_at=detected_at,
            raw_data={"opportunity": opp, "amount": amount},
            company_name=awardee_name,
            samgov_uei=uei,
            naics_codes=naics,
        ))


def _parse_sam_date(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:19], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None
