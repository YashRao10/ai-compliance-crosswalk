"""CLI entry point.

    python run.py --render portfolio-sync
    python run.py --render do178c-build-test

Renders an existing findings/<subject>-findings.json into reports/*.{json,html}.
Does not perform assessment itself — see README.md for how findings are produced.
"""

import argparse

from report import write_report


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", metavar="SUBJECT", required=True)
    args = parser.parse_args()
    json_path, html_path = write_report(args.render)
    print(f"Wrote {json_path}")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    run()
