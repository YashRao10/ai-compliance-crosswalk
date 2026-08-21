"""Tracks Gap/flagged findings to resolution over time — an append-only log,
not a script that decides status on its own. This is the piece that lets the
tool close its own NIST-MANAGE gap: a finding that's found but never tracked
to resolution is exactly what scored Gap for both subjects in the first
crosswalk run.

Status values: "open" -> "in_progress" -> "resolved". Append a new entry with
a later date to change status; never edit or delete a past entry (it's a log,
not a mutable field).
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LOG_PATH = REPO_ROOT / "remediation_log.json"

VALID_STATUSES = {"open", "in_progress", "resolved"}


def load_log(path: Path = LOG_PATH) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    for e in entries:
        if e["status"] not in VALID_STATUSES:
            raise ValueError(f"Invalid remediation status: {e['status']} ({e['subject']}/{e['control_id']})")
    return entries


def current_status(entries: list[dict]) -> dict:
    """Returns {(subject, control_id): latest_entry}, keyed by the most
    recent date per key. Ties (same date) keep the later entry in file order,
    since that's the more-recently-written one."""
    latest = {}
    for entry in entries:
        key = (entry["subject"], entry["control_id"])
        existing = latest.get(key)
        if existing is None or entry["date"] >= existing["date"]:
            latest[key] = entry
    return latest


def history_for(entries: list[dict], subject: str, control_id: str) -> list[dict]:
    return sorted(
        (e for e in entries if e["subject"] == subject and e["control_id"] == control_id),
        key=lambda e: e["date"],
    )
