import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from remediation import VALID_STATUSES, current_status, history_for, load_log


def test_loads_real_log():
    entries = load_log()
    assert len(entries) > 0
    for e in entries:
        assert e["status"] in VALID_STATUSES


def test_current_status_picks_latest_per_key():
    entries = [
        {"subject": "s1", "control_id": "C1", "status": "open", "date": "2026-01-01", "note": "found"},
        {"subject": "s1", "control_id": "C1", "status": "in_progress", "date": "2026-02-01", "note": "working on it"},
        {"subject": "s1", "control_id": "C2", "status": "open", "date": "2026-01-15", "note": "unrelated"},
    ]
    latest = current_status(entries)
    assert latest[("s1", "C1")]["status"] == "in_progress"
    assert latest[("s1", "C2")]["status"] == "open"


def test_history_for_returns_sorted_full_timeline():
    entries = [
        {"subject": "s1", "control_id": "C1", "status": "in_progress", "date": "2026-02-01", "note": "b"},
        {"subject": "s1", "control_id": "C1", "status": "open", "date": "2026-01-01", "note": "a"},
        {"subject": "s2", "control_id": "C1", "status": "open", "date": "2026-01-01", "note": "different subject"},
    ]
    timeline = history_for(entries, "s1", "C1")
    assert [e["date"] for e in timeline] == ["2026-01-01", "2026-02-01"]


def test_rejects_invalid_status(tmp_path):
    bad_log = tmp_path / "bad_log.json"
    bad_log.write_text(
        '{"entries": [{"subject": "s1", "control_id": "C1", "status": "not_a_real_status", "date": "2026-01-01", "note": "x"}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid remediation status"):
        load_log(bad_log)


def test_missing_log_returns_empty_list(tmp_path):
    assert load_log(tmp_path / "does_not_exist.json") == []
