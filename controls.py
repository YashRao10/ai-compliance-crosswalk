"""Loads and validates controls.yaml — the reference library of EU AI Act
articles and NIST AI RMF functions this tool crosswalks evidence against."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent
CONTROLS_PATH = REPO_ROOT / "controls.yaml"

REQUIRED_FIELDS = {"id", "framework", "title", "description", "what_would_satisfy_this"}
VALID_FRAMEWORKS = {"eu-ai-act", "nist-ai-rmf"}


def load_controls(path: Path = CONTROLS_PATH) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    controls = data.get("controls", [])
    if not controls:
        raise ValueError(f"No controls found in {path}")

    seen_ids = set()
    for control in controls:
        missing = REQUIRED_FIELDS - control.keys()
        if missing:
            raise ValueError(f"Control {control.get('id', '?')} missing fields: {missing}")
        if control["framework"] not in VALID_FRAMEWORKS:
            raise ValueError(
                f"Control {control['id']} has unknown framework: {control['framework']}"
            )
        if control["id"] in seen_ids:
            raise ValueError(f"Duplicate control id: {control['id']}")
        seen_ids.add(control["id"])

    return controls


def controls_by_id(path: Path = CONTROLS_PATH) -> dict[str, dict]:
    return {c["id"]: c for c in load_controls(path)}
