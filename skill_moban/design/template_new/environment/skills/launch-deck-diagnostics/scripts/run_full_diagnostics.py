#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parent
DECK_HTML_PATH = Path(os.environ.get("OUTPUT_ROOT", "/app/output")) / "deck" / "index.html"
TRIAGE_ORDER = [
    "probe_manifest.py",
    "check_overflow.py",
    "check_navigation.py",
    "check_source_trace.py",
    "check_chart_and_diagram_coverage.py",
]


def build_order(*, final: bool, include_browser: bool, include_story_fidelity: bool) -> list[str]:
    order = list(TRIAGE_ORDER)
    if include_browser or final:
        order.append("check_browser_contract.py")
    if include_story_fidelity or final:
        order.append("check_story_fidelity.py")
    if final:
        order.extend(
            [
                "package_submission.py",
                "submit_deck.py",
            ]
        )
    return order


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run launch-deck diagnostics. By default this performs lightweight triage. "
            "Use --final to include heavier browser/content checks and the real packaging/submission chain."
        )
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="Include browser contract, story fidelity, packaging, and live submit.",
    )
    parser.add_argument(
        "--include-browser",
        action="store_true",
        help="Include the Playwright browser-contract check during non-final triage.",
    )
    parser.add_argument(
        "--include-story-fidelity",
        action="store_true",
        help="Include the stricter story-fidelity audit during non-final triage.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    order = build_order(
        final=args.final,
        include_browser=args.include_browser,
        include_story_fidelity=args.include_story_fidelity,
    )
    mode = "final" if args.final else "triage"
    print(f"==> mode: {mode}")

    for index, script_name in enumerate(order):
        if index == 1 and not DECK_HTML_PATH.exists():
            print(
                "==> deck missing\n"
                "Create /app/output/deck/index.html with the required six slide roles, "
                "then rerun run_full_diagnostics.py."
            )
            return
        script_path = SCRIPTS_ROOT / script_name
        print(f"==> {script_name}")
        completed = subprocess.run([sys.executable, str(script_path)], check=False)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
