#!/usr/bin/env python3

import sys
from pathlib import Path

from pypdf import PdfReader


OUTPUT_FILE = Path("/root/board_meeting_packet.pdf")
EXPECTED_PAGES = [
    ("agenda_brief.pdf", "AB-02", "Board Objectives Summary"),
    ("finance_review.pdf", "FR-01", "Revenue Overview"),
    ("finance_review.pdf", "FR-02", "Cash Flow Dashboard"),
    ("product_update.pdf", "PU-03", "Pilot Timeline Review"),
    ("governance_appendix.pdf", "GA-02", "Resolution Digest"),
    ("agenda_brief.pdf", "AB-01", "Opening Agenda"),
    ("product_update.pdf", "PU-01", "Product Roadmap"),
]


def fail(message):
    raise AssertionError(message)


def normalize(text):
    if text is None:
        return ""
    return " ".join(text.split())


def main():
    if not OUTPUT_FILE.exists():
        fail(f"Output file not found: {OUTPUT_FILE}")

    reader = PdfReader(str(OUTPUT_FILE))
    if len(reader.pages) != len(EXPECTED_PAGES):
        fail(f"Expected {len(EXPECTED_PAGES)} pages, found {len(reader.pages)}")

    for index, (source_name, marker, title) in enumerate(EXPECTED_PAGES, start=1):
        page = reader.pages[index - 1]
        text = normalize(page.extract_text())

        for token in (source_name, marker, title):
            if token not in text:
                fail(f"Page {index} is missing expected token: {token}")

        rotation = int(page.get("/Rotate", 0) or 0) % 360
        if rotation != 0:
            fail(f"Page {index} rotation should be 0 after correction, found {rotation}")

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if height <= width:
            fail(f"Page {index} should remain portrait after assembly")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"TEST FAILURE: {error}", file=sys.stderr)
        sys.exit(1)
