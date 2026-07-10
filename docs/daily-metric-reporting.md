# Daily Metric Reporting

Turns a daily downloaded data export into a row in a Google Sheet, with three
Claude Code subagents wrapping the deterministic pipeline scripts for the
parts that need judgment (messy exports, anomaly review, safe publishing).

## Layout

```
config/metrics.yaml       KPI definitions, column mapping, Google Sheet target
data/incoming/             drop today's downloaded CSV/XLSX export here
data/processed/            normalized output from ingest.py (<date>.csv)
data/reports/               computed KPIs from compute_metrics.py (<date>_metrics.json)
scripts/ingest.py           normalize a raw export into the canonical schema
scripts/compute_metrics.py  compute KPIs + day-over-day anomaly flags
scripts/publish_to_sheets.py append the day's row to Google Sheets
scripts/daily_report.py     runs all three in sequence
.claude/agents/              data-wrangler, metrics-calculator, sheets-publisher
```

## One-time setup

1. `pip install -r requirements.txt`
2. Edit `config/metrics.yaml`:
   - `source_columns`: map each canonical field to the exact column header
     your daily export uses.
   - `metrics`: the KPIs to compute (sum/mean/max/min/last/count aggregates,
     or a `formula` derived from other columns/metrics).
   - `google_sheet.spreadsheet_id` / `worksheet_name`: the destination sheet.
3. Create a Google Cloud service account with the Sheets API enabled,
   download its JSON key, and share the target spreadsheet with the service
   account's email as **Editor**.
4. Set `GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/key.json` in your environment.

## Running it manually

```bash
cd scripts
python daily_report.py --input ../data/incoming/2026-07-10.csv --date 2026-07-10
```

Add `--dry-run` to see what would be published without writing to Sheets
(useful before credentials are configured, or to sanity-check a new export
format).

You can also run each stage independently:

```bash
python ingest.py --input ../data/incoming/2026-07-10.csv --date 2026-07-10
python compute_metrics.py --date 2026-07-10
python publish_to_sheets.py --date 2026-07-10
```

## Running it as agents

Once a file lands in `data/incoming/`, invoke the subagents in order (each
one calls the script above and adds judgment around edge cases):

1. **data-wrangler** — normalizes the export, fixing stale column mappings
   and flagging genuinely missing data instead of guessing.
2. **metrics-calculator** — computes the KPIs and gives a plain-English read
   on any day-over-day anomalies before anything gets published.
3. **sheets-publisher** — publishes the reviewed report, falling back to
   `--dry-run` and explaining what's missing if Sheets credentials aren't
   configured yet.

## Automating the daily run

To run this automatically every day, wire up a Routine (or any scheduler)
that drops the day's export into `data/incoming/` and then runs
`scripts/daily_report.py` — or invokes the three subagents in order if you
want the anomaly review step to happen before publishing.
