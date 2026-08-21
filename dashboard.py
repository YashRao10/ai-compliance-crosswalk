"""Combined dashboard: all subjects, one page. Reads the same findings/*.json
files report.py reads, adds no new assessment logic — pure presentation layer,
built per the dataviz skill's method (status palette from its validated
reference, stat tiles, a legend-backed stacked bar, a cross-subject matrix,
a remediation tracker backed by remediation_log.json, and a coverage-history
view backed by history.json).

Usage:
    python dashboard.py
"""

import html
from datetime import datetime, timezone
from pathlib import Path

from controls import load_controls
from history import dates_for, load_history, record_snapshot
from remediation import current_status, history_for, load_log
from report import REPORTS_DIR, compute_summary, load_findings

SUBJECTS = ["portfolio-sync", "do178c-build-test", "self-learning-agent"]

# Validated status palette (dataviz skill, references/palette.md) — dark-surface
# steps, already clear 3:1 on a dark surface and distinct from the ai-security
# sibling project's teal accent.
STATUS = {
    "Met": {"hex": "#0ca30c", "text_on_fill": "#ffffff", "label": "Met"},
    "Partial": {"hex": "#fab219", "text_on_fill": "#1a1400", "label": "Partial"},
    "Gap": {"hex": "#d03b3b", "text_on_fill": "#ffffff", "label": "Gap"},
}
COVERAGE_ICON = {"Met": "✓", "Partial": "◑", "Gap": "✕"}

REMEDIATION_STATUS = {
    "open": {"hex": "#d03b3b", "text_on_fill": "#ffffff", "label": "Open"},
    "in_progress": {"hex": "#fab219", "text_on_fill": "#1a1400", "label": "In progress"},
    "resolved": {"hex": "#0ca30c", "text_on_fill": "#ffffff", "label": "Resolved"},
}

FRAMEWORK_LABEL = {"eu-ai-act": "EU AI Act", "nist-ai-rmf": "NIST AI RMF"}


def load_all_findings() -> dict:
    return {subject: load_findings(subject) for subject in SUBJECTS}


def findings_lookup(findings_data: dict) -> dict:
    return {f["control_id"]: f for f in findings_data["findings"]}


# ---------- stat tiles / bars / legend ----------

def render_stat_tile(value: int, label: str, color: str = None) -> str:
    style = f' style="color:{color}"' if color else ""
    return f'<div class="stat-tile"><div class="stat-value"{style}>{value}</div><div class="stat-label">{html.escape(label)}</div></div>'


def render_subject_bar(subject: str, summary: dict) -> str:
    total = summary["total"]
    segments = []
    for key in ("Met", "Partial", "Gap"):
        count = summary[key]
        if count == 0:
            continue
        meta = STATUS[key]
        pct = round(count / total * 100, 1)
        show_label = count >= 2
        label_html = f'<span class="bar-seg-label" style="color:{meta["text_on_fill"]}">{count}</span>' if show_label else ""
        segments.append(
            f'<div class="bar-seg" style="flex:{count} 0 0;background:{meta["hex"]}" '
            f'title="{meta["label"]}: {count} of {total} ({pct}%)">{label_html}</div>'
        )
    return f'<div class="subject-bar-row"><div class="subject-bar-label">{html.escape(subject)}</div><div class="subject-bar">{"".join(segments)}</div></div>'


def render_legend() -> str:
    swatches = "".join(
        f'<span class="legend-item"><span class="legend-swatch" style="background:{meta["hex"]}"></span>{meta["label"]}</span>'
        for meta in STATUS.values()
    )
    return f'<div class="legend">{swatches}</div>'


# ---------- ticker ----------

def render_ticker(controls: list, all_findings: dict) -> str:
    controls_by_id = {c["id"]: c for c in controls}
    pills = []
    for subject in SUBJECTS:
        for f in all_findings[subject]["findings"]:
            control = controls_by_id[f["control_id"]]
            meta = STATUS[f["coverage"]]
            flag = " ⚠" if f.get("needs_human_review") else ""
            pills.append(
                f'<span class="ticker-pill"><span class="ticker-dot" style="background:{meta["hex"]}"></span>'
                f'{html.escape(subject)} &middot; {html.escape(f["control_id"])} &middot; {html.escape(control["title"].split("—")[-1].strip())} '
                f'&middot; <strong>{f["coverage"]}</strong>{flag}</span>'
            )
    track = "".join(pills)
    # Duplicated once so the CSS animation can loop seamlessly at -50%.
    return f'<div class="ticker" role="marquee" aria-label="All control verdicts, all subjects"><div class="ticker-track">{track}{track}</div></div>'


# ---------- filters ----------

FILTER_BAR = """
<div class="filter-bar">
  <input type="text" id="search-input" class="search-input" placeholder="Search controls, rationale...">
  <div class="filter-group" data-filter-type="coverage">
    <span class="filter-group-label">Coverage</span>
    <button class="filter-btn active" data-value="all">All</button>
    <button class="filter-btn" data-value="Met">Met</button>
    <button class="filter-btn" data-value="Partial">Partial</button>
    <button class="filter-btn" data-value="Gap">Gap</button>
    <button class="filter-btn" data-value="flagged">Flagged</button>
  </div>
  <div class="filter-group" data-filter-type="framework">
    <span class="filter-group-label">Framework</span>
    <button class="filter-btn active" data-value="all">All</button>
    <button class="filter-btn" data-value="eu-ai-act">EU AI Act</button>
    <button class="filter-btn" data-value="nist-ai-rmf">NIST RMF</button>
  </div>
</div>
"""

FILTER_SCRIPT = """
<script>
function copyAnchorLink(btn) {
  var url = location.href.split('#')[0] + '#' + btn.dataset.anchor;
  var done = function() {
    var original = btn.innerHTML;
    btn.innerHTML = '&#10003;';
    setTimeout(function() { btn.innerHTML = original; }, 1200);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(done, done);
  } else {
    done();
  }
}

(function() {
  var toggleBtn = document.getElementById('theme-toggle');
  function syncIcon() {
    var isLight = document.documentElement.getAttribute('data-theme') === 'light';
    toggleBtn.innerHTML = isLight ? '&#9789;' : '&#9788;';
  }
  syncIcon();
  toggleBtn.addEventListener('click', function() {
    var next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('crosswalk-theme', next); } catch (e) {}
    syncIcon();
  });
})();

(function() {
  var state = { coverage: 'all', framework: 'all', search: '' };

  function applyFilters() {
    document.querySelectorAll('[data-coverage][data-framework]').forEach(function(el) {
      var covOk = state.coverage === 'all'
        || (state.coverage === 'flagged' ? el.dataset.flagged === '1' : el.dataset.coverage === state.coverage);
      var fwOk = state.framework === 'all' || el.dataset.framework === state.framework;
      var searchOk = !state.search || el.textContent.toLowerCase().indexOf(state.search) !== -1;
      el.style.display = (covOk && fwOk && searchOk) ? '' : 'none';
    });
    document.querySelectorAll('.matrix-framework-row').forEach(function(headerRow) {
      var anyVisible = false;
      var sib = headerRow.nextElementSibling;
      while (sib && !sib.classList.contains('matrix-framework-row')) {
        if (sib.style.display !== 'none') { anyVisible = true; break; }
        sib = sib.nextElementSibling;
      }
      headerRow.style.display = anyVisible ? '' : 'none';
    });
  }

  document.querySelectorAll('.filter-group').forEach(function(group) {
    var type = group.dataset.filterType;
    group.querySelectorAll('.filter-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        group.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        state[type] = btn.dataset.value;
        applyFilters();
      });
    });
  });

  var searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', function() {
      state.search = searchInput.value.trim().toLowerCase();
      applyFilters();
    });
  }

  function openTargetFromHash() {
    if (!location.hash) return;
    var el;
    try { el = document.querySelector(location.hash); } catch (e) { return; }
    if (el && el.tagName === 'DETAILS') {
      el.open = true;
      setTimeout(function() { el.scrollIntoView({behavior: 'smooth', block: 'center'}); }, 30);
    }
  }
  window.addEventListener('DOMContentLoaded', openTargetFromHash);
  window.addEventListener('hashchange', openTargetFromHash);
  openTargetFromHash();

  window.addEventListener('beforeprint', function() {
    document.querySelectorAll('details').forEach(function(d) {
      d.dataset.wasOpen = d.open ? '1' : '0';
      d.open = true;
    });
  });
  window.addEventListener('afterprint', function() {
    document.querySelectorAll('details').forEach(function(d) {
      d.open = d.dataset.wasOpen === '1';
    });
  });
})();
</script>
"""


# ---------- matrix ----------

def render_matrix_cell(finding: dict | None, anchor: str) -> str:
    if finding is None:
        return '<td class="matrix-cell matrix-cell-empty">&mdash;</td>'
    coverage = finding["coverage"]
    meta = STATUS[coverage]
    flag = " ⚠" if finding.get("needs_human_review") else ""
    return (
        f'<td class="matrix-cell">'
        f'<a class="matrix-badge" href="#{anchor}" style="background:{meta["hex"]};color:{meta["text_on_fill"]}" '
        f'title="{html.escape(finding["rationale"][:180])}">{COVERAGE_ICON[coverage]}{flag}</a>'
        f'</td>'
    )


def render_matrix(controls: list, all_findings: dict) -> str:
    lookups = {s: findings_lookup(all_findings[s]) for s in SUBJECTS}
    rows = []
    current_framework = None
    for control in controls:
        if control["framework"] != current_framework:
            current_framework = control["framework"]
            rows.append(
                f'<tr class="matrix-framework-row" data-framework="{current_framework}">'
                f'<td colspan="{2 + len(SUBJECTS)}">{FRAMEWORK_LABEL[current_framework]}</td></tr>'
            )
        # A row can carry multiple subjects' findings; use the worse-case coverage
        # (Gap > Partial > Met) for the row-level filter attribute so filtering
        # by "Gap" surfaces a row if EITHER subject gapped on it.
        rank = {"Gap": 0, "Partial": 1, "Met": 2}
        row_findings = [lookups[s].get(control["id"]) for s in SUBJECTS]
        present = [f for f in row_findings if f]
        worst_coverage = min(present, key=lambda f: rank[f["coverage"]])["coverage"] if present else "Met"
        any_flagged = "1" if any(f.get("needs_human_review") for f in present) else "0"

        cells = "".join(
            render_matrix_cell(lookups[s].get(control["id"]), anchor=f"{s}-{control['id']}")
            for s in SUBJECTS
        )
        rows.append(
            f'<tr data-coverage="{worst_coverage}" data-framework="{control["framework"]}" data-flagged="{any_flagged}">'
            f'<td class="matrix-control-id">{html.escape(control["id"])}</td>'
            f'<td class="matrix-control-title">{html.escape(control["title"])}</td>'
            f'{cells}</tr>'
        )
    header_cells = "".join(f"<th>{html.escape(s)}</th>" for s in SUBJECTS)
    return f'<table class="matrix"><thead><tr><th>Control</th><th></th>{header_cells}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


# ---------- remediation tracker ----------

def render_remediation_tracker(controls_by_id: dict, all_findings: dict) -> str:
    entries = load_log()
    statuses = current_status(entries)

    if not statuses:
        return '<p class="empty-note">No tracked findings — nothing scored Gap and nothing was flagged for review.</p>'

    blocks = []
    for subject in SUBJECTS:
        items = [(key, latest) for key, latest in statuses.items() if key[0] == subject]
        if not items:
            continue
        rows = []
        for (subj, control_id), latest in sorted(items, key=lambda kv: kv[0][1]):
            control = controls_by_id[control_id]
            meta = REMEDIATION_STATUS[latest["status"]]
            hist = history_for(entries, subj, control_id)
            hist_html = ""
            if len(hist) > 1:
                hist_items = "".join(
                    f'<li>{html.escape(h["date"])} &mdash; <strong>{REMEDIATION_STATUS[h["status"]]["label"]}</strong>: {html.escape(h["note"])}</li>'
                    for h in hist
                )
                hist_html = f'<ol class="remediation-history">{hist_items}</ol>'
            rows.append(f"""
            <div class="remediation-item">
              <div class="remediation-item-head">
                <span class="badge" style="background:{meta['hex']};color:{meta['text_on_fill']}">{meta['label']}</span>
                <span class="control-id">{html.escape(control_id)}</span>
                <span class="control-title">{html.escape(control['title'])}</span>
                <span class="remediation-date">since {html.escape(latest['date'])}</span>
              </div>
              <div class="remediation-note">{html.escape(latest['note'])}</div>
              {hist_html}
            </div>
            """)
        blocks.append(f'<div class="remediation-subject-block"><div class="remediation-subject">{html.escape(subject)}</div>{"".join(rows)}</div>')
    return "".join(blocks)


# ---------- history ----------

def render_history(runs: list) -> str:
    if not runs:
        return '<p class="empty-note">No history yet.</p>'
    blocks = []
    for subject in SUBJECTS:
        subject_runs = dates_for(runs, subject)
        if not subject_runs:
            continue
        rows = "".join(
            f'<tr><td class="history-date">{html.escape(r["date"])}</td>'
            f'<td style="color:{STATUS["Met"]["hex"]}">{r["Met"]}</td>'
            f'<td style="color:{STATUS["Partial"]["hex"]}">{r["Partial"]}</td>'
            f'<td style="color:{STATUS["Gap"]["hex"]}">{r["Gap"]}</td>'
            f'<td>{r["needs_human_review"]}</td></tr>'
            for r in subject_runs
        )
        note = (
            '<p class="empty-note">Only one assessment run so far — this table becomes a trend chart once more accumulate.</p>'
            if len(subject_runs) < 3 else ""
        )
        blocks.append(f"""
        <div class="history-block">
          <div class="remediation-subject">{html.escape(subject)}</div>
          <table class="history-table">
            <thead><tr><th>Date</th><th>Met</th><th>Partial</th><th>Gap</th><th>Flagged</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
          {note}
        </div>
        """)
    return "".join(blocks)


# ---------- detail cards ----------

def render_detail_card(subject: str, finding: dict, control: dict) -> str:
    meta = STATUS[finding["coverage"]]
    flag_html = ""
    if finding.get("needs_human_review"):
        flag_html = f'<div class="flag">NEEDS HUMAN REVIEW &mdash; {html.escape(finding.get("human_review_reason", ""))}</div>'
    anchor = f"{subject}-{control['id']}"
    flagged_attr = "1" if finding.get("needs_human_review") else "0"
    return f"""
    <details class="card" id="{anchor}" data-coverage="{finding['coverage']}" data-framework="{control['framework']}" data-flagged="{flagged_attr}">
      <summary>
        <span class="badge" style="background:{meta['hex']};color:{meta['text_on_fill']}">{finding['coverage']}</span>
        <span class="control-id">{html.escape(control['id'])}</span>
        <span class="control-title">{html.escape(control['title'])}</span>
        <button class="copy-link-btn" data-anchor="{anchor}" title="Copy link to this control" onclick="event.preventDefault();event.stopPropagation();copyAnchorLink(this)">&#128279;</button>
      </summary>
      <div class="card-body">
        <div class="field"><span class="field-label">What would satisfy this</span>{html.escape(control['what_would_satisfy_this'].strip())}</div>
        <div class="field"><span class="field-label">Rationale</span>{html.escape(finding['rationale'])}</div>
        <div class="field"><span class="field-label">Confidence</span>{html.escape(finding['confidence'])}</div>
        {flag_html}
      </div>
    </details>
    """


def render_subject_section(subject: str, findings_data: dict, controls: list) -> str:
    lookup = findings_lookup(findings_data)
    cards = "\n".join(render_detail_card(subject, lookup[c["id"]], c) for c in controls if c["id"] in lookup)
    return f'<section><h2>{html.escape(subject)} &mdash; full detail</h2><div class="cards">{cards}</div></section>'


# ---------- page ----------

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AI Compliance Crosswalk — Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0a0d10">
<meta property="og:type" content="website">
<meta property="og:title" content="AI Compliance Crosswalk">
<meta property="og:description" content="Real AI agents checked against EU AI Act Articles 9-15 and NIST AI RMF -- every verdict written in-session against real evidence, not scored by a script.">
<meta property="og:url" content="https://yashrao10.github.io/ai-compliance-crosswalk/">
<meta property="og:image" content="https://yashrao10.github.io/ai-compliance-crosswalk/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="AI Compliance Crosswalk">
<meta name="twitter:description" content="Real AI agents checked against EU AI Act Articles 9-15 and NIST AI RMF -- every verdict written in-session against real evidence, not scored by a script.">
<meta name="twitter:image" content="https://yashrao10.github.io/ai-compliance-crosswalk/og-image.png">
<script>
  // Runs before first paint so there's no flash of the wrong theme.
  (function() {{
    var stored = null;
    try {{ stored = localStorage.getItem('crosswalk-theme'); }} catch (e) {{}}
    var theme = stored || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    document.documentElement.setAttribute('data-theme', theme);
  }})();
</script>
<style>
  :root{{
    --bg:#0a0d10; --panel:#11161b; --panel-2:#161c22;
    --ink:#e8eaed; --ink-2:#9aa4ae; --ink-faint:#5b6570;
    --accent:#2dd4bf; --accent-ink:#04211d; --rule:#232a31;
    --glow-1: rgba(45,212,191,0.14); --glow-2: rgba(208,59,59,0.07); --glow-3: rgba(10,163,12,0.06);
    --grid-line: rgba(255,255,255,0.025);
    --mono: Consolas,'SF Mono','Cascadia Code','Courier New',monospace;
    --sans: 'Segoe UI',system-ui,-apple-system,sans-serif;
  }}
  :root[data-theme="light"]{{
    --bg:#f9f9f7; --panel:#fcfcfb; --panel-2:#f2f1ed;
    --ink:#0b0b0b; --ink-2:#52514e; --ink-faint:#898781;
    --accent:#0d9488; --accent-ink:#ffffff; --rule:#e1e0d9;
    --glow-1: rgba(13,148,136,0.08); --glow-2: rgba(208,59,59,0.05); --glow-3: rgba(10,163,12,0.05);
    --grid-line: rgba(11,11,11,0.035);
  }}
  *{{box-sizing:border-box}}
  html,body{{margin:0;padding:0;background:var(--bg)}}
  body{{
    color:var(--ink);font-family:var(--sans);line-height:1.5;padding:0 0 100px;
    background-color:var(--bg);
    background-image:
      radial-gradient(ellipse 1100px 620px at 18% -8%, var(--glow-1), transparent 60%),
      radial-gradient(ellipse 900px 560px at 100% 8%, var(--glow-2), transparent 62%),
      radial-gradient(ellipse 800px 700px at 92% 92%, var(--glow-3), transparent 60%),
      linear-gradient(var(--grid-line) 1px, transparent 1px),
      linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
    background-size:auto,auto,auto,48px 48px,48px 48px;
    background-position:0 0,0 0,0 0,0 0,0 0;
    background-repeat:no-repeat,no-repeat,no-repeat,repeat,repeat;
    transition:background-color .15s ease,color .15s ease;
  }}
  /* No background-attachment:fixed — that forces a repaint on every scroll
     frame with layered gradients this size, which is what caused the lag. */
  .page{{max-width:1040px;margin:0 auto;padding:0 24px;position:relative}}

  .theme-toggle{{
    position:fixed;top:16px;right:20px;z-index:50;
    width:38px;height:38px;border-radius:50%;
    background:var(--panel);border:1px solid var(--rule);color:var(--ink);
    font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;
    box-shadow:0 2px 8px rgba(0,0,0,0.25);
  }}
  .theme-toggle:hover{{border-color:var(--accent)}}
  h1{{font-size:28px;font-weight:600;margin:0 0 4px}}
  .subtitle{{font-family:var(--mono);font-size:12px;color:var(--ink-faint);margin-bottom:20px}}
  .lede{{font-size:15px;color:var(--ink-2);max-width:760px;margin:0 0 28px;line-height:1.65}}
  .lede a{{color:var(--accent)}}
  .lede strong{{color:var(--ink)}}
  h2{{font-size:17px;font-weight:600;color:var(--accent);margin:0 0 14px}}
  section{{margin-bottom:44px}}
  .empty-note{{color:var(--ink-faint);font-size:13px;font-family:var(--mono)}}

  /* ticker */
  .ticker{{overflow:hidden;background:var(--panel);border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);margin-bottom:36px;white-space:nowrap}}
  .ticker-track{{display:inline-flex;animation:ticker-scroll 90s linear infinite}}
  @keyframes ticker-scroll{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
  @media (prefers-reduced-motion: reduce){{.ticker-track{{animation:none}}.ticker{{overflow-x:auto}}}}
  .ticker-pill{{display:inline-flex;align-items:center;gap:7px;padding:10px 22px;font-family:var(--mono);font-size:12px;color:var(--ink-2);border-right:1px solid var(--rule);flex-shrink:0}}
  .ticker-pill strong{{color:var(--ink)}}
  .ticker-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}

  .top-pad{{padding-top:36px}}

  .kpi-row{{display:flex;gap:12px;margin-bottom:8px}}
  .stat-tile{{flex:1;background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:16px;text-align:center}}
  .stat-value{{font-family:var(--sans);font-size:30px;font-weight:600;color:var(--ink)}}
  .stat-label{{font-family:var(--mono);font-size:10px;letter-spacing:0.06em;color:var(--ink-faint);text-transform:uppercase;margin-top:4px}}

  .legend{{display:flex;gap:18px;margin:18px 0;font-family:var(--mono);font-size:12px;color:var(--ink-2)}}
  .legend-item{{display:flex;align-items:center;gap:6px}}
  .legend-swatch{{width:12px;height:12px;border-radius:3px;display:inline-block}}

  .subject-bar-row{{display:flex;align-items:center;gap:16px;margin-bottom:14px}}
  .subject-bar-label{{width:150px;font-family:var(--mono);font-size:12.5px;color:var(--ink-2);flex-shrink:0}}
  .subject-bar{{flex:1;display:flex;height:22px;border-radius:4px;overflow:hidden;background:var(--panel-2)}}
  .bar-seg{{display:flex;align-items:center;justify-content:center;border-right:2px solid var(--bg)}}
  .bar-seg:last-child{{border-right:none}}
  .bar-seg-label{{font-family:var(--mono);font-size:11px;font-weight:700}}

  /* filters */
  .filter-bar{{
    display:flex;gap:20px;flex-wrap:wrap;align-items:center;margin-bottom:18px;padding:12px 14px;
    background:var(--panel);border:1px solid var(--rule);border-radius:8px;
    position:sticky;top:12px;z-index:15;
  }}
  .search-input{{
    font-family:var(--sans);font-size:13px;color:var(--ink);background:var(--panel-2);
    border:1px solid var(--rule);border-radius:20px;padding:6px 14px;min-width:220px;flex-shrink:0;
  }}
  .search-input::placeholder{{color:var(--ink-faint)}}
  .search-input:focus-visible{{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}}
  .filter-btn:focus-visible,.theme-toggle:focus-visible,.copy-link-btn:focus-visible,.matrix-badge:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
  .filter-group{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
  .filter-group-label{{font-family:var(--mono);font-size:10px;letter-spacing:0.06em;color:var(--ink-faint);text-transform:uppercase;margin-right:4px}}
  .filter-btn{{font-family:var(--mono);font-size:11.5px;color:var(--ink-2);background:var(--panel-2);border:1px solid var(--rule);border-radius:20px;padding:4px 12px;cursor:pointer}}
  .filter-btn:hover{{color:var(--ink)}}
  .filter-btn.active{{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:700}}

  table.matrix{{width:100%;border-collapse:collapse;font-size:13px}}
  table.matrix th{{text-align:left;font-family:var(--mono);font-size:10.5px;letter-spacing:0.05em;color:var(--ink-faint);text-transform:uppercase;padding:8px 10px;border-bottom:1px solid var(--rule)}}
  table.matrix td{{padding:8px 10px;border-bottom:1px solid var(--rule);vertical-align:middle}}
  .matrix-framework-row td{{background:var(--panel-2);font-family:var(--mono);font-size:11px;letter-spacing:0.06em;color:var(--accent);text-transform:uppercase;padding:6px 10px}}
  .matrix-control-id{{font-family:var(--mono);font-size:11.5px;color:var(--ink-2);white-space:nowrap}}
  .matrix-control-title{{color:var(--ink)}}
  .matrix-cell{{text-align:center;width:64px}}
  .matrix-cell-empty{{color:var(--ink-faint);text-align:center}}
  .matrix-badge{{display:inline-flex;align-items:center;justify-content:center;width:30px;height:24px;border-radius:5px;font-weight:700;font-size:13px;text-decoration:none}}

  .cards{{display:flex;flex-direction:column;gap:8px}}
  .card{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;overflow:hidden;scroll-margin-top:20px}}
  .card[open]{{border-color:#334049}}
  .card summary{{list-style:none;cursor:pointer;padding:12px 14px;display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:12.5px}}
  .card summary::-webkit-details-marker{{display:none}}
  .card summary:hover{{background:var(--panel-2)}}
  .badge{{font-weight:700;font-size:10.5px;letter-spacing:0.05em;padding:3px 8px;border-radius:5px;flex-shrink:0}}
  .control-id{{color:var(--ink);font-weight:600;flex-shrink:0}}
  .control-title{{color:var(--ink-2);flex:1}}
  .card-body{{padding:4px 14px 16px;border-top:1px solid var(--rule)}}
  .field{{margin-top:12px;font-size:13.5px;color:var(--ink)}}
  .field-label{{display:block;font-family:var(--mono);font-size:10px;letter-spacing:0.06em;color:var(--ink-faint);margin-bottom:4px;text-transform:uppercase}}
  .flag{{margin-top:12px;padding:8px 12px;border-left:3px solid #fab219;background:var(--panel-2);border-radius:0 6px 6px 0;font-size:12.5px;color:#fab219;font-family:var(--mono)}}

  /* remediation tracker */
  .remediation-subject-block{{margin-bottom:22px}}
  .remediation-subject{{font-family:var(--mono);font-size:11px;color:var(--ink-faint);text-transform:uppercase;letter-spacing:0.05em;margin:0 0 8px}}
  .remediation-item{{background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:12px 14px;margin-bottom:8px}}
  .remediation-item-head{{display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:12.5px;flex-wrap:wrap}}
  .remediation-date{{margin-left:auto;color:var(--ink-faint);font-size:11px}}
  .remediation-note{{margin-top:8px;font-size:13.5px;color:var(--ink-2)}}
  .remediation-history{{margin:10px 0 0;padding-left:18px;font-size:12px;color:var(--ink-faint)}}
  .remediation-history li{{margin-bottom:4px}}

  /* history */
  .history-block{{margin-bottom:22px}}
  table.history-table{{width:100%;border-collapse:collapse;font-size:13px}}
  table.history-table th{{text-align:left;font-family:var(--mono);font-size:10.5px;letter-spacing:0.05em;color:var(--ink-faint);text-transform:uppercase;padding:6px 10px;border-bottom:1px solid var(--rule)}}
  table.history-table td{{padding:6px 10px;border-bottom:1px solid var(--rule);font-family:var(--mono)}}
  .history-date{{color:var(--ink-2)}}

  .footer-note{{margin-top:40px;padding-top:16px;border-top:1px solid var(--rule);font-size:11.5px;color:var(--ink-faint);font-family:var(--mono)}}

  @page{{margin:18mm 14mm 22mm 14mm}}
  @media print{{
    .ticker,.filter-bar,.theme-toggle,.copy-link-btn{{display:none}}
    body{{background:#ffffff;color:#111}}
    h2,.lede a{{color:#0f766e}}
    .stat-tile,.card,.remediation-item,table.matrix,table.history-table{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  }}

  /* copy-link */
  .copy-link-btn{{
    background:none;border:none;color:var(--ink-faint);cursor:pointer;font-size:12px;
    padding:2px 4px;border-radius:4px;flex-shrink:0;line-height:1;
  }}
  .copy-link-btn:hover{{color:var(--accent);background:var(--panel-2)}}
</style>
</head>
<body>
  <button class="theme-toggle" id="theme-toggle" title="Toggle light/dark" aria-label="Toggle light/dark theme">&#9788;</button>
  {ticker}
  <div class="page top-pad">
  <h1>AI Compliance Crosswalk</h1>
  <div class="subtitle">EU AI Act Articles 9&ndash;15 &middot; NIST AI RMF Govern/Map/Measure/Manage &middot; assessed {assessed_at}</div>
  <p class="lede">
    Three real AI agents already running on this machine &mdash; <strong>portfolio-sync</strong>
    (Robinhood trade execution), <strong>do178c-build-test</strong> (WSL build/coverage
    automation), and <strong>self-learning-agent</strong> (a PACT browser extension with a
    hard-coded, red-team-tested confirmation gate on every write) &mdash; checked against
    every substantive EU AI Act high-risk-system requirement and all four NIST AI RMF
    functions. Each verdict below is grounded in real evidence: for the first two, the
    subject's own system prompt, red-team run history, and
    <a href="../../ai-security/GOVERNANCE.md">ai-security's governance notes</a>; for the
    third, its own project blueprint and live demo test record, since it was never run
    through ai-security's harness. Nothing here was keyword-matched or scored by a script
    &mdash; see the footer for why that matters.
  </p>

  <section>
    <div class="kpi-row">
      {kpi_tiles}
    </div>
  </section>

  <section>
    <h2>Coverage by subject</h2>
    {legend}
    {subject_bars}
  </section>

  <section>
    <h2>Cross-subject matrix</h2>
    {filter_bar}
    {matrix}
  </section>

  <section>
    <h2>Remediation tracker</h2>
    {remediation_html}
  </section>

  <section>
    <h2>History</h2>
    {history_html}
  </section>

  {subject_sections}

  <div class="footer-note">
    Coverage verdicts were reached in-session by Claude reading each control
    against real evidence (system prompt, red-team report, governance notes),
    not by keyword matching or a scripted API call. Click any matrix badge to
    jump to its full rationale below. This is a self-assessment, not an
    external conformity assessment. See README.md and PROMPT_INPUTS.md.
  </div>
  </div>
  {filter_script}
</body>
</html>
"""


def build() -> Path:
    controls = load_controls()
    controls_by_id_map = {c["id"]: c for c in controls}
    all_findings = load_all_findings()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    agg = {"Met": 0, "Partial": 0, "Gap": 0, "needs_human_review": 0, "total": 0}
    subject_bars = ""
    for subject in SUBJECTS:
        summary = compute_summary(all_findings[subject]["findings"])
        for k in agg:
            agg[k] += summary[k]
        subject_bars += render_subject_bar(subject, summary)
        record_snapshot(today, subject, summary)

    kpi_tiles = (
        render_stat_tile(agg["total"], "controls assessed")
        + render_stat_tile(agg["Met"], "met", STATUS["Met"]["hex"])
        + render_stat_tile(agg["Partial"], "partial", STATUS["Partial"]["hex"])
        + render_stat_tile(agg["Gap"], "gap", STATUS["Gap"]["hex"])
        + render_stat_tile(agg["needs_human_review"], "flagged for review")
    )

    subject_sections = "".join(
        render_subject_section(subject, all_findings[subject], controls) for subject in SUBJECTS
    )

    out = PAGE_TEMPLATE.format(
        ticker=render_ticker(controls, all_findings),
        assessed_at=html.escape(today),
        kpi_tiles=kpi_tiles,
        legend=render_legend(),
        subject_bars=subject_bars,
        filter_bar=FILTER_BAR,
        matrix=render_matrix(controls, all_findings),
        remediation_html=render_remediation_tracker(controls_by_id_map, all_findings),
        history_html=render_history(load_history()),
        subject_sections=subject_sections,
        filter_script=FILTER_SCRIPT,
    )

    REPORTS_DIR.mkdir(exist_ok=True)
    out_path = REPORTS_DIR / "dashboard.html"
    out_path.write_text(out, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
