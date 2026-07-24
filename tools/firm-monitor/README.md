# CIOS Target Firm Monitor

Tracks federal award activity for the 91-firm mid-market defense target list
(sourced from `91 Firms` Google Sheet) via the public USASpending.gov API.
Built for CIOS platform outreach targeting — not related to the DNV/Bastion
compliance portal.

## What it does

- **`enrich_naics.py`** — resolves each firm's primary NAICS code/description,
  UEI, and recipient ID from their USASpending award history. Run once, safe
  to rerun (skips firms already resolved unless `--force`).
- **`monitor.py`** — the weekly check. First run seeds a baseline of all
  known awards per firm (no alerts). Every run after that flags brand-new
  awards or awards whose amount/last-modified date changed, and appends them
  to `state/awards_log.csv`.
- **`dashboard.py`** — local read-only dashboard (`http://127.0.0.1:5050`)
  showing the firm list with NAICS/UEI and a feed of recent flagged awards.
  Has a "Run Check Now" button for manual runs.

## Setup

```bash
pip install -r requirements.txt
python enrich_naics.py      # populates data/firms.csv with NAICS + UEI
python monitor.py           # first run = baseline seed, no alerts
python dashboard.py         # http://127.0.0.1:5050
```

## Automating the weekly check

```powershell
powershell -ExecutionPolicy Bypass -File schedule_task.ps1
```

Registers a per-user Windows Scheduled Task (`CIOS Firm Monitor - Weekly
USASpending Check`) that runs `monitor.py` every Monday at 7:00 AM. No admin
rights needed. To remove it later:

```powershell
Unregister-ScheduledTask -TaskName "CIOS Firm Monitor - Weekly USASpending Check" -Confirm:$false
```

## Notes / limitations

- The source sheet has no UEIs, so matching is by company name
  (`recipient_search_text`) — generic names (e.g. "Launcher", "Component
  Control") can occasionally pull in unrelated awards. Review flagged rows
  before acting on them; `data/firms.csv` records each firm's resolved UEI
  once found so this gets more precise over time.
- Covers contracts, IDVs/task orders, and grants/cooperative agreements
  (the latter covers SBIR/STTR Phase I/II).
- `state/seen_awards.json` is the dedupe baseline — delete it to force a
  fresh baseline seed (re-running will NOT re-flag existing awards as new).

## Files

| Path | Purpose |
|---|---|
| `data/firms_seed.csv` | Original 91-firm list (name, industry, website) |
| `data/firms.csv` | Enriched, live-updated firm list |
| `state/seen_awards.json` | Dedupe baseline (award ID → amount/last-modified) |
| `state/awards_log.csv` | Append-only log of every flagged NEW/MODIFIED award |
| `state/run_log.txt` | One JSON line per monitor.py run |
