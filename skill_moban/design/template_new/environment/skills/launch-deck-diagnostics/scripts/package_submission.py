#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

from common import DECK_HTML_PATH, SUBMISSION_PATH, infer_slide_manifest_from_html, write_json


def main() -> None:
    slides = infer_slide_manifest_from_html()
    payload = {
        "job_id": f"launch-deck-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "entry_html": str(DECK_HTML_PATH),
        "slide_count": len(slides),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "slides": slides,
    }
    write_json(SUBMISSION_PATH, payload)
    print(f"Wrote {SUBMISSION_PATH}")


if __name__ == "__main__":
    main()
