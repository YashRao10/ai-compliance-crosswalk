"""Exports reports/dashboard.html to reports/dashboard.pdf via headless Edge.

Reuses the file:// URL recipe already proven out in this environment
(explicit C:/ drive, %20 for spaces, never a raw path with literal spaces —
Edge silently renders a blank/404 page as a valid-looking PDF otherwise,
which is why this script verifies real text landed in the output rather than
trusting a zero exit code).

Usage:
    python export_pdf.py
"""

import subprocess
import sys
from pathlib import Path

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

REPO_ROOT = Path(__file__).resolve().parent
HTML_PATH = REPO_ROOT / "reports" / "dashboard.html"
PDF_PATH = REPO_ROOT / "reports" / "dashboard.pdf"


def find_edge() -> str:
    for candidate in EDGE_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("Microsoft Edge not found at any known install path")


def to_file_url(path: Path) -> str:
    return "file:///" + str(path.resolve()).replace("\\", "/").replace(" ", "%20")


def export(html_path: Path = HTML_PATH, pdf_path: Path = PDF_PATH) -> Path:
    if not html_path.exists():
        raise FileNotFoundError(f"{html_path} doesn't exist — run dashboard.py first")

    edge = find_edge()
    file_url = to_file_url(html_path)
    subprocess.run(
        [
            edge, "--headless", "--disable-gpu",
            f"--print-to-pdf={pdf_path.resolve()}",
            "--print-to-pdf-no-header",
            file_url,
        ],
        check=True,
        capture_output=True,
    )

    if not pdf_path.exists() or pdf_path.stat().st_size < 2000:
        raise RuntimeError(f"PDF export looks wrong — {pdf_path} missing or suspiciously small")

    _verify_real_content(pdf_path)
    return pdf_path


def _verify_real_content(pdf_path: Path) -> None:
    """Guards against the known Edge failure mode: a blank/404 page silently
    rendered as a valid-looking PDF. Checks for text that can only appear if
    the real page rendered, not an error page."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    required = ["AI Compliance Crosswalk", "portfolio-sync", "do178c-build-test", "self-learning-agent"]
    missing = [r for r in required if r not in text]
    if missing:
        raise RuntimeError(
            f"PDF at {pdf_path} rendered but is missing expected content {missing} — "
            "likely a blank or error page, not the real dashboard. Do not trust this file."
        )
    if len(reader.pages) < 2:
        raise RuntimeError(f"PDF at {pdf_path} has only {len(reader.pages)} page(s) — expected multiple.")


if __name__ == "__main__":
    try:
        path = export()
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {path}")
