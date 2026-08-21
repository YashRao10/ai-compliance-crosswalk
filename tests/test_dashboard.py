import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard import STATUS, SUBJECTS, build
from report import load_findings


def test_build_writes_dashboard_html():
    out_path = build()
    assert out_path.exists()
    assert out_path.name == "dashboard.html"


def test_dashboard_contains_all_subjects():
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    for subject in SUBJECTS:
        assert subject in html


def test_dashboard_surfaces_flagged_findings_if_any_exist():
    """Same guarantee as report.py's test: a needs_human_review finding must
    be visible on the page, not silently folded into an aggregate count. Real
    findings currently have none (both EU-ART10 flags were resolved
    2026-08-18 — see remediation_log.json), so this only asserts the marker
    exists when the data actually has one; the unconditional guarantee lives
    in test_report.py's synthetic-fixture version of this same check."""
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    any_findings_flagged = False
    for subject in SUBJECTS:
        findings = load_findings(subject)["findings"]
        if any(f.get("needs_human_review") for f in findings):
            any_findings_flagged = True
    if any_findings_flagged:
        assert "NEEDS HUMAN REVIEW" in html
        assert "⚠" in html


def test_resolved_remediation_items_show_resolved_status():
    """EU-ART10 was resolved for both subjects on 2026-08-18 (see
    remediation_log.json) — this is the tool's own remediation tracker
    actually completing a find->track->resolve cycle, not just scaffolding.
    Guards against a resolved entry silently reverting to looking "open"."""
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    assert "Resolved" in html
    assert "EU-ART10" in html


def test_status_colors_all_clear_3_1_on_dark_surface():
    """Sanity check on the validated status palette actually in use — see
    dataviz skill references/palette.md. Full CVD/lightness validation was
    run separately via scripts/validate_palette.js; this just guards against
    someone swapping in an unvalidated hex later."""
    expected = {"Met": "#0ca30c", "Partial": "#fab219", "Gap": "#d03b3b"}
    for key, hex_value in expected.items():
        assert STATUS[key]["hex"] == hex_value


def test_dashboard_has_search_and_theme_toggle():
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    assert 'id="search-input"' in html
    assert 'id="theme-toggle"' in html


def test_dashboard_has_no_on_page_print_button():
    """The on-page print button was removed 2026-08-20 — export_pdf.py is
    the supported path to a PDF now. Its underlying pipeline (the
    beforeprint/afterprint listeners that expand every card, and the
    @media print stylesheet) stays, since headless Edge's --print-to-pdf
    still depends on both."""
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    assert "print-btn" not in html
    assert "beforeprint" in html
    assert "@media print" in html


def test_dashboard_has_light_theme_css_vars():
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    assert '[data-theme="light"]' in html


def test_dashboard_handles_deep_link_hash_on_load():
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    assert "openTargetFromHash" in html
    assert "el.open = true" in html


def test_copy_link_buttons_reference_real_anchors():
    out_path = build()
    html = out_path.read_text(encoding="utf-8")
    assert 'data-anchor="portfolio-sync-EU-ART14"' in html
    assert 'id="portfolio-sync-EU-ART14"' in html
