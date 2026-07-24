"""
dashboard.py — read-only dashboard for the CIOS target firm monitor.

Run: python dashboard.py   (serves on http://127.0.0.1:5050)
"""
from __future__ import annotations

import csv
from pathlib import Path

from flask import Flask, redirect, render_template, url_for

import monitor

ROOT = Path(__file__).parent
FIRMS_PATH = ROOT / "data" / "firms.csv"
LOG_PATH = ROOT / "state" / "awards_log.csv"

app = Flask(__name__)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@app.route("/")
def index():
    firms = read_csv(FIRMS_PATH)
    firms.sort(key=lambda f: f.get("company", "").lower())

    flags = read_csv(LOG_PATH)
    flags.reverse()  # most recent first (append-only log)

    resolved = sum(1 for f in firms if f.get("naics_code"))
    stats = {
        "total_firms": len(firms),
        "naics_resolved": resolved,
        "flagged_events": len(flags),
        "last_checked": max((f.get("last_checked", "") for f in firms), default="—") or "—",
    }
    return render_template("dashboard.html", firms=firms, flags=flags[:100], stats=stats)


@app.route("/run-check", methods=["POST"])
def run_check():
    monitor.run()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
