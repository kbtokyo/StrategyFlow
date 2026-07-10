#!/usr/bin/env python3
"""Publish a computed daily metrics report to Google Sheets.

Usage:
    python scripts/publish_to_sheets.py --date 2026-07-10
    python scripts/publish_to_sheets.py --date 2026-07-10 --dry-run

Reads data/reports/<date>_metrics.json (produced by compute_metrics.py) and
appends a row to the configured Google Sheet worksheet, creating a header
row on first use. Requires:

  - GOOGLE_SERVICE_ACCOUNT_JSON env var: path to a service account key file
  - config/metrics.yaml: google_sheet.spreadsheet_id and worksheet_name
  - The service account's email must be shared on the target sheet as Editor

See docs/daily-metric-reporting.md for setup steps. Pass --dry-run to
print what would be written without calling the Sheets API (useful for
testing before credentials are configured).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from common import load_config, parse_date, report_path_for

FORMATTERS = {
    "currency": lambda v: f"${v:,.2f}",
    "integer": lambda v: f"{v:,.0f}",
    "percent": lambda v: f"{v * 100:.1f}%",
}


def format_value(value, metric_config: dict):
    if value is None:
        return "N/A"
    fmt = metric_config.get("format")
    formatter = FORMATTERS.get(fmt)
    return formatter(value) if formatter else value


def build_row(report: dict, metrics_config: list[dict]) -> list:
    row = [report["date"]]
    for metric in metrics_config:
        row.append(format_value(report["values"].get(metric["name"]), metric))
    return row


def header_row(metrics_config: list[dict]) -> list:
    return ["Date"] + [m["name"] for m in metrics_config]


def publish(report: dict, config: dict, dry_run: bool) -> int:
    row = build_row(report, config["metrics"])
    header = header_row(config["metrics"])

    if dry_run:
        print("dry run - would write header:", header)
        print("dry run - would append row:", row)
        if report["anomalies"]:
            print("anomalies to flag in sheet:", report["anomalies"])
        return 0

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print(
            "error: gspread/google-auth not installed. Run 'pip install -r "
            "requirements.txt' or use --dry-run.",
            file=sys.stderr,
        )
        return 1

    key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not key_path:
        print("error: GOOGLE_SERVICE_ACCOUNT_JSON env var is not set.", file=sys.stderr)
        return 1

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    client = gspread.authorize(creds)

    sheet_cfg = config["google_sheet"]
    spreadsheet = client.open_by_key(sheet_cfg["spreadsheet_id"])
    try:
        worksheet = spreadsheet.worksheet(sheet_cfg["worksheet_name"])
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=sheet_cfg["worksheet_name"], rows=1000, cols=len(header) + 1
        )
        worksheet.append_row(header)

    if worksheet.row_count == 0 or not worksheet.get_all_values():
        worksheet.append_row(header)

    worksheet.append_row(row)
    print(f"published {report['date']} metrics to '{sheet_cfg['worksheet_name']}'")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=None, help="Report date (YYYY-MM-DD), defaults to today")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be published without calling Sheets API"
    )
    args = parser.parse_args()

    date = parse_date(args.date)
    config = load_config()

    report_path = report_path_for(date)
    if not report_path.exists():
        print(
            f"error: no report at {report_path}. Run compute_metrics.py for this date first.",
            file=sys.stderr,
        )
        return 1

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    return publish(report, config, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
