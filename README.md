# AI Compliance Crosswalk

[![Tests](https://github.com/YashRao10/ai-compliance-crosswalk/actions/workflows/tests.yml/badge.svg)](https://github.com/YashRao10/ai-compliance-crosswalk/actions/workflows/tests.yml)

Maps EU AI Act (high-risk system Articles 9-15) and NIST AI RMF (Govern/Map/Measure/Manage)
requirements to real evidence for an AI system, and produces a gap report: what's
covered, what's partial, what's missing, and what needs a human decision rather
than an automated guess.

## Why this exists

Built off two things already in this environment:

- **`../ai-security/GOVERNANCE.md`** — a NIST AI RMF self-audit with Govern and
  Map filled in, but Measure and Manage left as placeholders pending a real run.
  This tool's first job was closing that gap using ai-security's own existing
  red-team reports as evidence (they existed but GOVERNANCE.md hadn't caught up
  to them).
- **`../PACT Work/05-Demo-Projects/AAS-DO178-Demo/requirements/10-DO330-Qualification-Case-Study.md`** —
  proved out a reusable gap-analysis shape (crosswalk table → coverage matrix →
  honest verdict → numbered remediation paths) for DO-330 tool qualification.
  This tool applies the same shape to EU AI Act / NIST RMF controls instead of
  Tool Operational Requirements.

## How assessment works (read this before trusting a report)

Coverage verdicts are **not** produced by a script, keyword matcher, or scripted
API call. `report.py` is a pure formatter — it renders whatever is already in
`findings/<subject>-findings.json`, but does not decide what goes in it.

Findings are written **in-session**: Claude reads a control's description
alongside the subject's actual evidence (system prompt, red-team report,
governance notes — see `evidence.py`), writes a coverage verdict (`Met` /
`Partial` / `Gap`) with a plain-English rationale and a confidence level, then
does a self-review pass before treating the set as final. Anything genuinely
uncertain is marked `needs_human_review: true` with a `human_review_reason` —
this is a hard rule, not a suggestion, because `ai-security/harness/classifier.py`
had a real negation-blindness bug (a refusal that quoted the forbidden phrase
back got misclassified as a violation) that only got caught because a human
read the transcript. A bare pass/fail here would reintroduce that same failure
mode one layer up.

This means: no `ANTHROPIC_API_KEY`, no `anthropic` dependency, and reports
can't be regenerated for a new subject without Claude back in the loop to do
the reading. That trade-off was made deliberately (see the plan this project
was built from) — it buys rationale-per-verdict and a structural defense
against the exact bug class already found in this environment, at the cost of
not being a fire-and-forget script.

## Quickstart

```
pip install -r requirements.txt
python dashboard.py
```

Writes `reports/dashboard.html` — one combined page covering all subjects.
Self-contained, open directly in a browser, no server needed. What's on it:

- **Ticker** — every control verdict for both subjects, scrolling (pauses
  automatically if the browser has reduced-motion set).
- **KPI row + coverage bars** — aggregate stats and a Met/Partial/Gap bar per
  subject.
- **Cross-subject matrix** — all 11 controls × 2 subjects in one table.
  Click a badge to jump straight to its full rationale (auto-opens the card).
- **Search + filters** — free-text search plus Coverage/Framework filters,
  applied together, live.
- **Remediation tracker** — backed by `remediation_log.json`, an append-only
  log (`open` → `in_progress` → `resolved`). This is the part that matters
  most: it's what actually closes the tool's own NIST-MANAGE finding — a
  result found but never tracked to resolution is exactly what scored Gap.
- **History** — `history.json` gets a snapshot per subject on every build.
  One date exists so far; it's a table until there's enough data for a real
  trend chart.
- **Light/dark toggle + copy-link buttons** — top-right; theme choice is
  remembered via `localStorage`. Copy-link puts a direct URL to that control
  on the clipboard (same feature as the YR Hub public site).
- No on-page print button — `export_pdf.py` (below) is the supported path
  to a PDF. Its underlying pipeline still lives in the page itself: a
  dedicated print stylesheet (hides the ticker/filters/toggles, expands
  every card, forces background colors to print) that headless Edge's
  `--print-to-pdf` uses directly.

Colors are the dataviz skill's validated status palette (not the ad hoc hex
values ai-security's own report uses), chosen so Met/Partial/Gap are
distinguishable under color-vision deficiency and never rely on color alone
(every badge carries an icon and a text label too). The same palette is used
in both themes — only surface/text tokens swap for light mode.

For a PDF instead of (or alongside) the HTML:

```
python export_pdf.py
```

Writes `reports/dashboard.pdf` via headless Edge, and actually verifies real
text landed in the output before calling it done — Edge has a known failure
mode where a malformed `file://` URL silently renders a blank/404 page as a
valid-looking PDF, so a zero exit code alone isn't trusted here.

For a single-subject view instead of the combined dashboard:

```
python run.py --render portfolio-sync
python run.py --render do178c-build-test
```

Writes `reports/<subject>-<timestamp>.html`.

To assess a new subject: register its evidence in `evidence.py` — either add
it to `SUBJECT_PROMPT_FILES` if it has an ai-security system prompt and
red-team report, or to `SUBJECT_DOC_FILES` if it's assessed from its own
project documents instead (the pattern `self-learning-agent` uses, since it
was never run through ai-security's harness) — then write
`findings/<subject>-findings.json` following the shape of the existing
files (one entry per control in `controls.yaml`, each with `coverage`,
`rationale`, `confidence`, `needs_human_review`), add the subject to
`SUBJECTS` in `dashboard.py`, and render it. To track a Gap or flagged
finding to resolution over time, append (never edit) a new entry to
`remediation_log.json` with a later `date`.

## Project layout

```
controls.yaml               reference library — EU AI Act Art. 9-15 + NIST RMF's 4 functions
controls.py                  loads/validates controls.yaml
evidence.py                   loaders for ai-security's system prompts + red-team reports,
                                and for subjects assessed from their own project docs instead
findings/<subject>.json        Claude-authored verdicts (see "How assessment works" above)
remediation_log.json           append-only find -> track -> resolve log
remediation.py                  loads the log, resolves current status per (subject, control)
history.json                   per-build coverage snapshots (written to reports/, not tracked here)
history.py                      records/reads snapshots
report.py                       pure formatter -> single-subject HTML/JSON
dashboard.py                     pure formatter -> combined HTML site (the primary view)
export_pdf.py                    headless-Edge PDF export with real content verification
run.py                          CLI: python run.py --render <subject>
tests/                          pytest — controls, report rendering, dashboard rendering, remediation log, history plumbing
reports/                        generated output (gitignored)
```

## Tests

```
pip install -r requirements-dev.txt
pytest tests/
```

35 tests as of this writing, covering: `controls.yaml` structure validation,
`report.py`'s single-subject rendering (including that a flagged/low-confidence
finding is never silently dropped), `dashboard.py`'s combined rendering
(search/toggle/print markup present, deep-link JS present, copy-link anchors
match real card IDs), `remediation.py`'s log parsing and status resolution,
and `history.py`'s snapshot recording/deduping.
