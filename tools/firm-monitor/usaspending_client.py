"""
usaspending_client.py — thin wrapper around the public USASpending.gov API.

No API key required. Docs: https://api.usaspending.gov/docs/endpoints
"""
from __future__ import annotations

import time
import requests

API_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# The API requires award_type_codes to come from a single group per call.
AWARD_TYPES_CONTRACTS = ["A", "B", "C", "D"]
AWARD_TYPES_IDVS = ["IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"]
# Grants + cooperative agreements (covers SBIR/STTR Phase I/II)
AWARD_TYPES_GRANTS = ["02", "03", "04", "05"]

AWARD_TYPE_GROUPS = [AWARD_TYPES_CONTRACTS, AWARD_TYPES_IDVS, AWARD_TYPES_GRANTS]

FIELDS = [
    "Award ID", "Recipient Name", "Recipient UEI", "Start Date", "End Date",
    "Last Modified Date", "Award Amount", "Awarding Agency", "Awarding Sub Agency",
    "Award Type", "NAICS", "recipient_id", "generated_internal_id",
]

_last_call = 0.0
_MIN_INTERVAL = 0.35  # be polite to a free public API


def _throttle() -> None:
    global _last_call
    wait = _MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()


def search_awards(recipient_name: str, start_date: str, end_date: str,
                   award_type_codes: list[str], limit: int = 100) -> list[dict]:
    """Query spending_by_award for one recipient name. Returns [] on any error."""
    payload = {
        "filters": {
            "recipient_search_text": [recipient_name],
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": award_type_codes,
        },
        "fields": FIELDS,
        "page": 1,
        "limit": limit,
        "sort": "Start Date",
        "order": "desc",
    }
    _throttle()
    try:
        resp = requests.post(API_URL, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as e:
        print(f"  ! API error for {recipient_name!r}: {e}")
        return []


def search_all_award_types(recipient_name: str, start_date: str, end_date: str,
                            limit: int = 100) -> list[dict]:
    """Contracts + IDVs + grants combined for one recipient (each is its own API call)."""
    results: list[dict] = []
    for group in AWARD_TYPE_GROUPS:
        results += search_awards(recipient_name, start_date, end_date, group, limit)
    return results
