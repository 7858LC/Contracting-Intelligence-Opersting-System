"""
monitor.py — weekly USASpending check for the CIOS target firm list.

First run: seeds a baseline of every award currently on record for each firm
(no flags emitted — there's nothing to compare against yet).

Every run after that: re-pulls a rolling window of recent award activity,
diffs it against the baseline, and appends any brand-new award or any award
whose amount/Last Modified Date changed to state/awards_log.csv.

Usage:
    python monitor.py
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from usaspending_client import search_all_award_types

ROOT = Path(__file__).parent
FIRMS_PATH = ROOT / "data" / "firms.csv"
SEEN_PATH = ROOT / "state" / "seen_awards.json"
LOG_PATH = ROOT / "state" / "awards_log.csv"
RUN_LOG_PATH = ROOT / "state" / "run_log.txt"

# How far back each incremental run looks for new/changed award activity
ROLLING_WINDOW_DAYS = 180
BASELINE_LOOKBACK_START = "2015-01-01"

LOG_FIELDNAMES = [
    "flagged_at", "event_type", "company", "award_id", "agency",
    "award_amount", "naics_code", "naics_description",
    "start_date", "last_modified_date",
]


def load_firms() -> list[dict]:
    if not FIRMS_PATH.exists():
        raise SystemExit(f"{FIRMS_PATH} not found — run enrich_naics.py first")
    with open(FIRMS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_firms(firms: list[dict], fieldnames: list[str]) -> None:
    with open(FIRMS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(firms)


def load_seen() -> dict:
    if SEEN_PATH.exists():
        return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    return {}


def save_seen(seen: dict) -> None:
    SEEN_PATH.parent.mkdir(exist_ok=True)
    SEEN_PATH.write_text(json.dumps(seen, indent=2), encoding="utf-8")


def append_log(rows: list[dict]) -> None:
    if not rows:
        return
    is_new = not LOG_PATH.exists()
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerows(rows)


def fingerprint(award: dict) -> tuple:
    return (award.get("Award Amount"), award.get("Last Modified Date"))


def run() -> dict:
    firms = load_firms()
    fieldnames = list(firms[0].keys()) if firms else []
    seen = load_seen()
    baseline_run = len(seen) == 0

    today = date.today()
    today_iso = today.isoformat()
    window_start = (today - timedelta(days=ROLLING_WINDOW_DAYS)).isoformat()
    start_date = BASELINE_LOOKBACK_START if baseline_run else window_start

    flagged: list[dict] = []
    new_count = 0
    modified_count = 0

    for firm in firms:
        company = firm["company"]
        results = search_all_award_types(company, start_date, today_iso, limit=100)

        max_start = firm.get("last_award_date", "") or ""
        for award in results:
            gid = award.get("generated_internal_id")
            if not gid:
                continue
            fp = fingerprint(award)
            sd = award.get("Start Date") or ""
            if sd > max_start:
                max_start = sd

            prior = seen.get(gid)
            if prior is None:
                seen[gid] = {"amount": fp[0], "last_modified": fp[1], "company": company}
                if not baseline_run:
                    new_count += 1
                    flagged.append(_log_row("NEW_AWARD", company, award))
            elif (prior.get("amount"), prior.get("last_modified")) != fp:
                seen[gid] = {"amount": fp[0], "last_modified": fp[1], "company": company}
                modified_count += 1
                flagged.append(_log_row("MODIFIED", company, award))

        firm["last_checked"] = today_iso
        if max_start:
            firm["last_award_date"] = max_start

    save_firms(firms, fieldnames)
    save_seen(seen)
    append_log(flagged)

    summary = {
        "run_at": today_iso,
        "baseline_run": baseline_run,
        "firms_checked": len(firms),
        "new_awards": new_count,
        "modified_awards": modified_count,
    }
    RUN_LOG_PATH.parent.mkdir(exist_ok=True)
    with open(RUN_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")
    return summary


def _log_row(event_type: str, company: str, award: dict) -> dict:
    naics = award.get("NAICS") or {}
    return {
        "flagged_at": date.today().isoformat(),
        "event_type": event_type,
        "company": company,
        "award_id": award.get("Award ID", ""),
        "agency": award.get("Awarding Agency", ""),
        "award_amount": award.get("Award Amount", ""),
        "naics_code": naics.get("code", ""),
        "naics_description": naics.get("description", ""),
        "start_date": award.get("Start Date", ""),
        "last_modified_date": award.get("Last Modified Date", ""),
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
