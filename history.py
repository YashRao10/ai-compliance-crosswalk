"""Plumbing for a coverage-over-time view. Every dashboard build appends (or
updates, if run again same day) a snapshot per subject. Only one date exists
as of this writing — this sets up real trend data for future re-assessments
rather than faking a trend out of a single point now."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
HISTORY_PATH = REPO_ROOT / "reports" / "history.json"


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8")).get("runs", [])


def record_snapshot(date: str, subject: str, summary: dict) -> list[dict]:
    runs = load_history()
    row = {
        "date": date,
        "subject": subject,
        "Met": summary["Met"],
        "Partial": summary["Partial"],
        "Gap": summary["Gap"],
        "needs_human_review": summary["needs_human_review"],
        "total": summary["total"],
    }
    runs = [r for r in runs if not (r["date"] == date and r["subject"] == subject)]
    runs.append(row)
    runs.sort(key=lambda r: (r["date"], r["subject"]))

    HISTORY_PATH.parent.mkdir(exist_ok=True)
    HISTORY_PATH.write_text(json.dumps({"runs": runs}, indent=2), encoding="utf-8")
    return runs


def dates_for(runs: list[dict], subject: str) -> list[dict]:
    return sorted((r for r in runs if r["subject"] == subject), key=lambda r: r["date"])
