#!/usr/bin/env python3
"""Compute the day's KPIs from a normalized data file and flag anomalies.

Usage:
    python scripts/compute_metrics.py --date 2026-07-10

Reads data/processed/<date>.csv (produced by ingest.py), computes every
metric defined in config/metrics.yaml, compares each against the prior
day's report (if one exists) and flags any that moved more than
`anomaly_threshold`. Writes the result to data/reports/<date>_metrics.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

import pandas as pd

from common import load_config, parse_date, processed_path_for, report_path_for, REPORTS_DIR

AGG_FUNCS = {
    "sum": lambda s: s.sum(),
    "mean": lambda s: s.mean(),
    "max": lambda s: s.max(),
    "min": lambda s: s.min(),
    "last": lambda s: s.iloc[-1],
    "count": lambda s: s.count(),
}


def compute_aggregates(df: pd.DataFrame, metrics_config: list[dict]) -> dict:
    values: dict[str, float] = {}
    # First pass: direct aggregates.
    for metric in metrics_config:
        if metric.get("agg") == "derived":
            continue
        column = metric["source"]
        if column not in df.columns:
            raise ValueError(f"metric '{metric['name']}' references unknown column '{column}'")
        agg_fn = AGG_FUNCS.get(metric["agg"])
        if agg_fn is None:
            raise ValueError(f"metric '{metric['name']}' has unsupported agg '{metric['agg']}'")
        values[metric["name"]] = float(agg_fn(pd.to_numeric(df[column], errors="coerce")))

    # Second pass: formulas, which may reference raw normalized columns
    # (aggregated via sum/last as available) as well as already-computed
    # metric values.
    column_totals = {
        col: float(pd.to_numeric(df[col], errors="coerce").sum())
        for col in df.columns
        if col != "date"
    }
    eval_namespace = {**column_totals, **values}
    for metric in metrics_config:
        if metric.get("agg") != "derived":
            continue
        formula = metric["formula"]
        try:
            # Restricted eval: only names already in the namespace and
            # basic arithmetic operators are usable.
            values[metric["name"]] = float(
                eval(formula, {"__builtins__": {}}, eval_namespace)  # noqa: S307
            )
        except ZeroDivisionError:
            values[metric["name"]] = None

    return values


def load_previous_report(date: dt.date) -> dict | None:
    previous_date = date - dt.timedelta(days=1)
    path = report_path_for(previous_date)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def flag_anomalies(values: dict, previous: dict | None, threshold: float) -> dict:
    anomalies = {}
    if not previous:
        return anomalies
    prev_values = previous.get("values", {})
    for name, value in values.items():
        prev = prev_values.get(name)
        if value is None or prev in (None, 0):
            continue
        change = abs(value - prev) / abs(prev)
        if change > threshold:
            anomalies[name] = {
                "previous": prev,
                "current": value,
                "change_pct": round(change * 100, 1),
            }
    return anomalies


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=None, help="Report date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    date = parse_date(args.date)
    config = load_config()

    processed_path = processed_path_for(date)
    if not processed_path.exists():
        print(
            f"error: no normalized data at {processed_path}. Run ingest.py for this date first.",
            file=sys.stderr,
        )
        return 1

    df = pd.read_csv(processed_path)
    try:
        values = compute_aggregates(df, config["metrics"])
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    previous = load_previous_report(date)
    anomalies = flag_anomalies(values, previous, config.get("anomaly_threshold", 0.2))

    report = {
        "date": date.isoformat(),
        "values": values,
        "anomalies": anomalies,
        "row_count": len(df),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = report_path_for(date)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"wrote metrics for {date.isoformat()} to {out_path}")
    if anomalies:
        print(f"anomalies flagged: {list(anomalies.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
