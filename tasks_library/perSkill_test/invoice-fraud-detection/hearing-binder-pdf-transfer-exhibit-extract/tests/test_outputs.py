import json
import os
import re

from pypdf import PdfReader


OUTPUT_PATH = "/root/hearing_exhibit_bundle.pdf"
SOURCE_PATH = "/root/hearing_materials_mixed_source"
MANIFEST_PATH = "/root/bundle_manifest.json"

HEADER_RE = re.compile(
    r"Case:\s*(?P<case_id>HB-\d{2}-\d{3})\s+"
    r"Exhibit:\s*(?P<exhibit_id>EX-\d{2})\s+"
    r"Exhibit Page:\s*(?P<page>\d+)\s+of\s+\d+"
)


def normalize(text: str) -> str:
    return " ".join((text or "").split())


def source_page_lookup():
    reader = PdfReader(SOURCE_PATH)
    lookup = {}

    for page in reader.pages:
        text = normalize(page.extract_text())
        match = HEADER_RE.search(text)
        assert match is not None, "Source page header could not be parsed."
        key = (
            match.group("case_id"),
            match.group("exhibit_id"),
            int(match.group("page")),
        )
        lookup[key] = {
            "text": text,
            "width": float(page.mediabox.width),
            "height": float(page.mediabox.height),
        }

    return lookup


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists(OUTPUT_PATH)

    def test_bundle_matches_manifest_order(self):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)

        lookup = source_page_lookup()
        expected_pages = []

        for request in manifest["requests"]:
            for exhibit_page in range(request["start_page"], request["end_page"] + 1):
                key = (request["case_id"], request["exhibit_id"], exhibit_page)
                assert key in lookup, f"Requested source page not found: {key}"
                expected_pages.append(lookup[key])

        output_reader = PdfReader(OUTPUT_PATH)
        assert len(output_reader.pages) == len(expected_pages), (
            f"Expected {len(expected_pages)} pages, got {len(output_reader.pages)}"
        )

        for index, (output_page, expected) in enumerate(
            zip(output_reader.pages, expected_pages), start=1
        ):
            output_text = normalize(output_page.extract_text())
            assert output_text == expected["text"], (
                f"Output page {index} does not match the required source page content."
            )

            assert abs(float(output_page.mediabox.width) - expected["width"]) < 0.01
            assert abs(float(output_page.mediabox.height) - expected["height"]) < 0.01
