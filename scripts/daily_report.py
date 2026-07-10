#!/usr/bin/env python3
"""Run the full daily metric reporting pipeline: ingest -> compute -> publish.

Usage:
    python scripts/daily_report.py --input data/incoming/2026-07-10.csv
    python scripts/daily_report.py --input data/incoming/2026-07-10.csv --date 2026-07-10 --dry-run
"""
from __future__ import annotations

import argparse
import sys

import compute_metrics
import ingest
import publish_to_sheets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the downloaded CSV/XLSX file")
    parser.add_argument("--date", default=None, help="Report date (YYYY-MM-DD), defaults to today")
    parser.add_argument(
        "--dry-run", action="store_true", help="Skip the Google Sheets write, print what would be sent"
    )
    args = parser.parse_args()

    common_args = ["--date", args.date] if args.date else []
    return _run(args, common_args)


def _run(args, common_args) -> int:
    ingest_argv = ["--input", args.input] + common_args
    sys.argv = ["ingest.py"] + ingest_argv
    rc = ingest.main()
    if rc != 0:
        return rc

    sys.argv = ["compute_metrics.py"] + common_args
    rc = compute_metrics.main()
    if rc != 0:
        return rc

    publish_argv = common_args + (["--dry-run"] if args.dry_run else [])
    sys.argv = ["publish_to_sheets.py"] + publish_argv
    return publish_to_sheets.main()


if __name__ == "__main__":
    raise SystemExit(main())
