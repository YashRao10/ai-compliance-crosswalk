import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import history as history_module
from history import dates_for, load_history, record_snapshot


def test_record_snapshot_writes_and_dedupes(tmp_path, monkeypatch):
    fake_path = tmp_path / "history.json"
    monkeypatch.setattr(history_module, "HISTORY_PATH", fake_path)

    summary = {"Met": 3, "Partial": 6, "Gap": 2, "needs_human_review": 1, "total": 11}
    record_snapshot("2026-08-18", "portfolio-sync", summary)
    runs = record_snapshot("2026-08-18", "portfolio-sync", summary)

    assert len(runs) == 1
    assert runs[0]["Met"] == 3


def test_record_snapshot_keeps_separate_dates_and_subjects(tmp_path, monkeypatch):
    fake_path = tmp_path / "history.json"
    monkeypatch.setattr(history_module, "HISTORY_PATH", fake_path)

    summary_a = {"Met": 3, "Partial": 6, "Gap": 2, "needs_human_review": 1, "total": 11}
    summary_b = {"Met": 5, "Partial": 4, "Gap": 2, "needs_human_review": 1, "total": 11}
    record_snapshot("2026-08-18", "portfolio-sync", summary_a)
    record_snapshot("2026-08-18", "do178c-build-test", summary_b)
    runs = record_snapshot("2026-09-01", "portfolio-sync", summary_a)

    assert len(runs) == 3
    assert load_history() == runs


def test_dates_for_filters_by_subject():
    runs = [
        {"date": "2026-08-18", "subject": "portfolio-sync", "Met": 3, "Partial": 6, "Gap": 2, "needs_human_review": 1, "total": 11},
        {"date": "2026-08-18", "subject": "do178c-build-test", "Met": 5, "Partial": 4, "Gap": 2, "needs_human_review": 1, "total": 11},
    ]
    assert len(dates_for(runs, "portfolio-sync")) == 1
    assert dates_for(runs, "portfolio-sync")[0]["subject"] == "portfolio-sync"
