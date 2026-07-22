"""
enrich_naics.py — one-time (rerunnable) pass to attach NAICS code, UEI, and
recipient_id to each firm in data/firms.csv, sourced from their USASpending
award history.

Usage:
    python enrich_naics.py            # only fills firms missing naics_code
    python enrich_naics.py --force    # re-resolves every firm
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from usaspending_client import search_all_award_types

ROOT = Path(__file__).parent
SEED_PATH = ROOT / "data" / "firms_seed.csv"
FIRMS_PATH = ROOT / "data" / "firms.csv"

FIELDNAMES = [
    "id", "company", "industry", "website",
    "naics_code", "naics_description", "all_naics",
    "uei", "recipient_id",
    "last_award_date", "last_checked", "total_awards_found",
]

LOOKBACK_START = "2015-01-01"


def load_firms() -> list[dict]:
    if FIRMS_PATH.exists():
        with open(FIRMS_PATH, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    with open(SEED_PATH, newline="", encoding="utf-8") as f:
        seed = list(csv.DictReader(f))
    for row in seed:
        for col in FIELDNAMES:
            row.setdefault(col, "")
    return seed


def save_firms(firms: list[dict]) -> None:
    with open(FIRMS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(firms)


def resolve_naics(company: str) -> dict:
    today = date.today().isoformat()
    results = search_all_award_types(company, LOOKBACK_START, today, limit=100)
    if not results:
        return {}

    naics_counts: Counter[tuple[str, str]] = Counter()
    uei = ""
    recipient_id = ""
    last_award_date = ""
    for r in results:
        naics = r.get("NAICS") or {}
        code, desc = naics.get("code"), naics.get("description")
        if code:
            naics_counts[(code, desc or "")] += 1
        if not uei and r.get("Recipient UEI"):
            uei = r["Recipient UEI"]
        if not recipient_id and r.get("recipient_id"):
            recipient_id = r["recipient_id"]
        sd = r.get("Start Date") or ""
        if sd > last_award_date:
            last_award_date = sd

    primary_code, primary_desc = ("", "")
    if naics_counts:
        (primary_code, primary_desc), _ = naics_counts.most_common(1)[0]

    all_naics = "; ".join(f"{c}: {d}" for (c, d), _ in naics_counts.most_common())

    return {
        "naics_code": primary_code,
        "naics_description": primary_desc,
        "all_naics": all_naics,
        "uei": uei,
        "recipient_id": recipient_id,
        "last_award_date": last_award_date,
        "total_awards_found": str(len(results)),
    }


def main() -> None:
    force = "--force" in sys.argv
    firms = load_firms()

    todo = [f for f in firms if force or not f.get("naics_code")]
    print(f"{len(todo)} of {len(firms)} firms need NAICS resolution\n")

    for i, firm in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {firm['company']}...", end=" ")
        info = resolve_naics(firm["company"])
        if info:
            firm.update(info)
            print(f"NAICS {info['naics_code']} ({info['total_awards_found']} awards)")
        else:
            print("no awards found")

    save_firms(firms)
    print(f"\nSaved {FIRMS_PATH}")


if __name__ == "__main__":
    main()
