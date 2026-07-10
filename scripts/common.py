"""Shared helpers for the daily metric reporting pipeline."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "metrics.yaml"
INCOMING_DIR = REPO_ROOT / "data" / "incoming"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "data" / "reports"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_date(value: str | None) -> dt.date:
    if value is None:
        return dt.date.today()
    return dt.date.fromisoformat(value)


def processed_path_for(date: dt.date) -> Path:
    return PROCESSED_DIR / f"{date.isoformat()}.csv"


def report_path_for(date: dt.date) -> Path:
    return REPORTS_DIR / f"{date.isoformat()}_metrics.json"
