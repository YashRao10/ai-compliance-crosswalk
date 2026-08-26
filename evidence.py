"""Loaders for the evidence this tool crosswalks controls against.

Wired to ai-security's two existing subjects (portfolio-sync,
do178c-build-test), reusing its system prompts and red-team run reports
directly rather than duplicating them. Subjects that never ran through
ai-security's own harness (e.g. self-learning-agent, a browser extension
assessed from its own project documents instead) are supported via
SUBJECT_DOC_FILES — a set of real files read as freeform text, so future
subjects beyond ai-security's two don't require touching its fixed
conventions.
"""

import json
from pathlib import Path

AI_SECURITY_ROOT = Path(__file__).resolve().parent.parent / "ai-security"
PACT_WORK_ROOT = Path(__file__).resolve().parent.parent / "PACT Work"

SUBJECT_PROMPT_FILES = {
    "portfolio-sync": AI_SECURITY_ROOT / "targets" / "portfolio_sync_system_prompt.md",
    "do178c-build-test": AI_SECURITY_ROOT / "targets" / "do178c_build_test_system_prompt.md",
}

# Optional Annex IV-style technical documentation package, where one has been
# written to close a real EU-ART11 Gap finding. Not every subject has one —
# absence just means gather_evidence omits the field, not an error.
SUBJECT_TECH_DOC_FILES = {
    "portfolio-sync": AI_SECURITY_ROOT / "targets" / "portfolio_sync_technical_documentation.md",
}

# Subjects assessed from real project documents instead of ai-security's
# system-prompt/red-team-report convention, because they were never run
# through that harness. Each entry: subject -> [(label, path), ...].
SUBJECT_DOC_FILES = {
    "self-learning-agent": [
        ("blueprint", PACT_WORK_ROOT / "07-Self-Learning-Agent" / "Self-Learning-Agent-Notes.md"),
        ("demo_summary_2026-08-18", PACT_WORK_ROOT / "07-Self-Learning-Agent" / "SLA-Demo-Summary-2026-08-18.html"),
        ("extension_readme", PACT_WORK_ROOT / "08-Self-Learning-Extension" / "README.md"),
    ],
}

# Latest re-graded report covering both subjects (2026-08-04) — supersedes
# the 2026-07-23 run, which used the classifier before its negation-handling
# fix.
LATEST_REDTEAM_REPORT = AI_SECURITY_ROOT / "reports" / "redteam-report-20260804-092949-manual.json"


def load_system_prompt(subject: str) -> str:
    path = SUBJECT_PROMPT_FILES.get(subject)
    if path is None:
        raise ValueError(f"No system prompt registered for subject: {subject}")
    return path.read_text(encoding="utf-8")


def load_redteam_results(subject: str) -> dict:
    """Returns the target's summary + full per-payload results from the
    latest ai-security red-team report, or None if the subject wasn't run."""
    report = json.loads(LATEST_REDTEAM_REPORT.read_text(encoding="utf-8"))
    for target in report["targets"]:
        if target["target"] == subject:
            return target
    return None


def load_governance_notes(subject: str) -> str:
    """Pulls the subject's own Govern + Map subsections out of
    ai-security/GOVERNANCE.md, since that doc is itself first-party evidence
    for the NIST-GOVERN and NIST-MAP controls."""
    text = (AI_SECURITY_ROOT / "GOVERNANCE.md").read_text(encoding="utf-8")
    marker = f"### {subject}"
    start = text.find(marker)
    if start == -1:
        return ""
    next_marker = text.find("###", start + len(marker))
    next_section = text.find("\n## ", start)
    end = min(x for x in (next_marker, next_section, len(text)) if x != -1)
    return text[start:end].strip()


def load_technical_documentation(subject: str) -> str:
    """Returns the subject's Annex IV-style technical documentation package,
    or empty string if none has been written for this subject yet."""
    path = SUBJECT_TECH_DOC_FILES.get(subject)
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_subject_documents(subject: str) -> dict:
    """Reads a subject's registered freeform documents as raw text, keyed
    by label. For subjects assessed outside ai-security's own conventions."""
    files = SUBJECT_DOC_FILES.get(subject)
    if files is None:
        raise ValueError(f"No documents registered for subject: {subject}")
    return {label: path.read_text(encoding="utf-8") for label, path in files}


def gather_evidence(subject: str) -> dict:
    """Bundles everything available for a subject into one dict, for a
    human (or Claude, in-session) to read before writing findings."""
    if subject in SUBJECT_PROMPT_FILES:
        evidence = {
            "subject": subject,
            "system_prompt": load_system_prompt(subject),
            "redteam_results": load_redteam_results(subject),
            "governance_notes": load_governance_notes(subject),
        }
        tech_doc = load_technical_documentation(subject)
        if tech_doc:
            evidence["technical_documentation"] = tech_doc
        return evidence
    if subject in SUBJECT_DOC_FILES:
        return {
            "subject": subject,
            "documents": load_subject_documents(subject),
        }
    raise ValueError(f"No evidence registered for subject: {subject}")
