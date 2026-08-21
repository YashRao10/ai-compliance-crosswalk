import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from report import compute_summary, render_html, remediation_paths, verdict_text

SAMPLE_CONTROLS = {
    "EU-ART9": {
        "id": "EU-ART9",
        "framework": "eu-ai-act",
        "title": "Article 9 — Risk Management System",
        "description": "d",
        "what_would_satisfy_this": "w",
    },
    "EU-ART10": {
        "id": "EU-ART10",
        "framework": "eu-ai-act",
        "title": "Article 10 — Data and Data Governance",
        "description": "d",
        "what_would_satisfy_this": "w",
    },
    "NIST-MANAGE": {
        "id": "NIST-MANAGE",
        "framework": "nist-ai-rmf",
        "title": "NIST AI RMF — Manage",
        "description": "d",
        "what_would_satisfy_this": "w",
    },
}

SAMPLE_FINDINGS_DATA = {
    "subject": "test-subject",
    "assessed_by": "test",
    "assessed_at_utc": "2026-08-18",
    "findings": [
        {"control_id": "EU-ART9", "coverage": "Met", "rationale": "solid evidence", "confidence": "high", "needs_human_review": False},
        {
            "control_id": "EU-ART10",
            "coverage": "Partial",
            "rationale": "ambiguous fit for this system type",
            "confidence": "medium",
            "needs_human_review": True,
            "human_review_reason": "unclear whether this article even applies",
        },
        {"control_id": "NIST-MANAGE", "coverage": "Gap", "rationale": "no tracked response", "confidence": "high", "needs_human_review": False},
    ],
}


def test_compute_summary_counts_each_coverage_level():
    summary = compute_summary(SAMPLE_FINDINGS_DATA["findings"])
    assert summary == {"Met": 1, "Partial": 1, "Gap": 1, "total": 3, "needs_human_review": 1}


def test_needs_human_review_is_never_silently_dropped():
    """The whole point of the in-session assessment design (see README.md /
    plan) is that low-confidence verdicts get surfaced, not averaged away
    like the classifier.py negation-blindness bug this project was designed
    to avoid. This test guards that property at the rendering layer."""
    summary = compute_summary(SAMPLE_FINDINGS_DATA["findings"])
    assert summary["needs_human_review"] == 1

    html_out = render_html("test-subject", SAMPLE_FINDINGS_DATA, SAMPLE_CONTROLS)
    assert "NEEDS HUMAN REVIEW" in html_out
    assert "unclear whether this article even applies" in html_out


def test_gap_findings_appear_in_remediation_paths():
    paths = remediation_paths(SAMPLE_FINDINGS_DATA["findings"], SAMPLE_CONTROLS)
    assert any("NIST AI RMF — Manage" in p for p in paths)


def test_needs_human_review_findings_appear_in_remediation_paths():
    paths = remediation_paths(SAMPLE_FINDINGS_DATA["findings"], SAMPLE_CONTROLS)
    assert any("unclear whether this article even applies" in p for p in paths)


def test_verdict_mentions_gap_and_flagged_counts():
    summary = compute_summary(SAMPLE_FINDINGS_DATA["findings"])
    text = verdict_text(summary)
    assert "1 control(s) have no real coverage yet" in text
    assert "1 finding(s) are flagged for human review" in text


def test_clean_run_gets_a_different_verdict():
    clean_findings = [
        {"control_id": "EU-ART9", "coverage": "Met", "rationale": "r", "confidence": "high", "needs_human_review": False},
    ]
    summary = compute_summary(clean_findings)
    text = verdict_text(summary)
    assert "No outright gaps" in text


def test_render_html_rejects_unknown_control_gracefully():
    findings_with_unknown = {
        **SAMPLE_FINDINGS_DATA,
        "findings": [{"control_id": "NOT-REAL", "coverage": "Met", "rationale": "r", "confidence": "high", "needs_human_review": False}],
    }
    with pytest.raises(KeyError):
        render_html("test-subject", findings_with_unknown, SAMPLE_CONTROLS)
