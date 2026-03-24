import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path("/root")
LETTER_SIZE = (612.0, 792.0)


def normalize(text: str) -> str:
    return " ".join((text or "").split())


def page_size(page) -> tuple[float, float]:
    return (float(page.mediabox.width), float(page.mediabox.height))


def expected_sequence(manifest: dict) -> list[tuple]:
    sequence = [
        (
            "generated",
            [
                manifest["book_title"],
                manifest["meeting_title"],
                f'Meeting Date: {manifest["meeting_date"]}',
                f'Meeting Time: {manifest["meeting_time"]}',
                f'Location: {manifest["meeting_location"]}',
                manifest["confidentiality_label"],
            ],
        )
    ]
    for section in manifest["sections"]:
        sequence.append(
            (
                "generated",
                [
                    f'Section {section["section_code"]}',
                    section["section_title"],
                    manifest["confidentiality_label"],
                ],
            )
        )
        for item in section["items"]:
            for page_number in item["pages"]:
                sequence.append(("source", item["file"], page_number))
    return sequence


class TestBoardBookAssembly:
    def test_file_exists(self):
        assert (ROOT / "board_book.pdf").exists()

    def test_page_sequence_and_content(self):
        manifest = json.loads((ROOT / "board_packet_manifest.json").read_text())
        output_reader = PdfReader(str(ROOT / "board_book.pdf"))
        sequence = expected_sequence(manifest)

        assert len(output_reader.pages) == len(sequence)

        for index, expected in enumerate(sequence):
            output_page = output_reader.pages[index]
            output_text = normalize(output_page.extract_text())

            if expected[0] == "generated":
                for required_line in expected[1]:
                    assert required_line in output_text, (
                        f"Expected generated page {index + 1} to contain {required_line!r}, "
                        f"but text was: {output_text!r}"
                    )
                assert page_size(output_page) == LETTER_SIZE
                continue

            _, filename, page_number = expected
            source_page = PdfReader(str(ROOT / filename)).pages[page_number - 1]
            source_text = normalize(source_page.extract_text())

            assert output_text == source_text, (
                f"Copied page mismatch at output page {index + 1}: "
                f"expected text from {filename} page {page_number}."
            )
            assert page_size(output_page) == page_size(source_page), (
                f"Page size mismatch at output page {index + 1}: "
                f"expected {page_size(source_page)}, got {page_size(output_page)}."
            )
