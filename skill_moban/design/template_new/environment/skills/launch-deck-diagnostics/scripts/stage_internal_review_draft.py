#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import DECK_HTML_PATH, INTERNAL_REVIEW_DRAFT_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage the internal-review draft into the formal deck output path.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing /app/output/deck/index.html instead of leaving it untouched.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not INTERNAL_REVIEW_DRAFT_PATH.exists():
        raise SystemExit(f"missing internal-review draft: {INTERNAL_REVIEW_DRAFT_PATH}")

    DECK_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DECK_HTML_PATH.exists() and not args.force:
        print(f"kept existing deck html: {DECK_HTML_PATH}")
        return

    shutil.copyfile(INTERNAL_REVIEW_DRAFT_PATH, DECK_HTML_PATH)
    print(f"staged internal-review draft to {DECK_HTML_PATH}")


if __name__ == "__main__":
    main()
