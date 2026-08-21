import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from controls import CONTROLS_PATH, load_controls, controls_by_id, REQUIRED_FIELDS, VALID_FRAMEWORKS


def test_loads_real_controls_file():
    controls = load_controls()
    assert len(controls) > 0


def test_every_control_has_required_fields():
    for control in load_controls():
        assert REQUIRED_FIELDS.issubset(control.keys())


def test_every_control_has_valid_framework():
    for control in load_controls():
        assert control["framework"] in VALID_FRAMEWORKS


def test_control_ids_are_unique():
    controls = load_controls()
    ids = [c["id"] for c in controls]
    assert len(ids) == len(set(ids))


def test_controls_by_id_indexes_correctly():
    by_id = controls_by_id()
    assert "EU-ART14" in by_id
    assert by_id["EU-ART14"]["title"].startswith("Article 14")


def test_expected_eu_ai_act_articles_present():
    by_id = controls_by_id()
    for article_num in [9, 10, 11, 12, 13, 14, 15]:
        assert f"EU-ART{article_num}" in by_id


def test_expected_nist_functions_present():
    by_id = controls_by_id()
    for fn in ["GOVERN", "MAP", "MEASURE", "MANAGE"]:
        assert f"NIST-{fn}" in by_id


def test_rejects_control_missing_a_field(tmp_path):
    bad_yaml = tmp_path / "bad_controls.yaml"
    bad_yaml.write_text(
        "controls:\n"
        "  - id: BAD-1\n"
        "    framework: eu-ai-act\n"
        "    title: Missing description and what_would_satisfy_this\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing fields"):
        load_controls(bad_yaml)


def test_rejects_unknown_framework(tmp_path):
    bad_yaml = tmp_path / "bad_controls.yaml"
    bad_yaml.write_text(
        "controls:\n"
        "  - id: BAD-1\n"
        "    framework: made-up-framework\n"
        "    title: t\n"
        "    description: d\n"
        "    what_would_satisfy_this: w\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown framework"):
        load_controls(bad_yaml)


def test_rejects_duplicate_ids(tmp_path):
    bad_yaml = tmp_path / "bad_controls.yaml"
    bad_yaml.write_text(
        "controls:\n"
        "  - id: DUP-1\n"
        "    framework: eu-ai-act\n"
        "    title: t\n"
        "    description: d\n"
        "    what_would_satisfy_this: w\n"
        "  - id: DUP-1\n"
        "    framework: eu-ai-act\n"
        "    title: t2\n"
        "    description: d2\n"
        "    what_would_satisfy_this: w2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate control id"):
        load_controls(bad_yaml)
