#!/usr/bin/env python3
"""Normalize a downloaded CSV/XLSX export into the pipeline's canonical format.

Usage:
    python scripts/ingest.py --input data/incoming/2026-07-10.csv --date 2026-07-10
    python scripts/ingest.py --input data/incoming/2026-07-10.xlsx

If --date is omitted, today's date is used. The normalized file is written
to data/processed/<date>.csv with columns renamed per config/metrics.yaml's
`source_columns` mapping.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from common import load_config, parse_date, processed_path_for, PROCESSED_DIR


def read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def normalize(df: pd.DataFrame, source_columns: dict) -> pd.DataFrame:
    missing = [raw for raw in source_columns.values() if raw not in df.columns]
    if missing:
        raise ValueError(
            f"Input file is missing expected column(s): {missing}. "
            f"Found columns: {list(df.columns)}. "
            "Update config/metrics.yaml's source_columns mapping if the "
            "export's headers changed."
        )
    rename_map = {raw: canonical for canonical, raw in source_columns.items()}
    normalized = df.rename(columns=rename_map)[list(rename_map.values())]
    normalized = normalized.dropna(how="all").drop_duplicates()
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the downloaded CSV/XLSX file")
    parser.add_argument("--date", default=None, help="Report date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 1

    date = parse_date(args.date)
    config = load_config()

    df = read_source(input_path)
    try:
        normalized = normalize(df, config["source_columns"])
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = processed_path_for(date)
    normalized.to_csv(out_path, index=False)
    print(f"wrote {len(normalized)} row(s) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
