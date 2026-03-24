import hashlib
import os
import re

from pypdf import PdfReader


INPUT_PDF = "/root/inspection_binder.pdf"
OUTPUT_PDF = "/root/site_inspection_packet.pdf"

EXPECTED_INPUT_SHA256 = "73c902621436c0cbb25574dfce1a98c09b899ad366d92ee0b6b049cace268c2b"
EXPECTED_PACKET_IDS = [
    "ST204-20260214-A",
    "ST204-20260214-B",
    "ST204-20260214-C",
    "ST204-20260303-A",
    "ST204-20260303-B",
    "ST204-20260303-C",
]
EXCLUDED_PACKET_IDS = [
    "ST110-20260214-A",
    "ST318-20260214-A",
    "ST204-20260221-A",
    "ST204-20260221-B",
    "ST110-20260303-C",
]
EXPECTED_PAGE_SNIPPETS = [
    ["Station Number: ST-204", "Inspection Date: 2026-02-14", "Section: Cover Sheet"],
    ["Continuation of previous inspection entry", "Section: Thermal Scan Images"],
    ["Station Number: ST-204", "Inspection Date: 2026-02-14", "Section: Safety Checklist"],
    ["Station Number: ST-204", "Inspection Date: 2026-03-03", "Section: Cover Sheet"],
    ["Continuation of previous inspection entry", "Section: Corrective Action Photos"],
    ["Station Number: ST-204", "Inspection Date: 2026-03-03", "Section: Technician Notes"],
]


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(text: str) -> str:
    return " ".join((text or "").split())


def main() -> None:
    assert os.path.exists(INPUT_PDF), f"Missing input file: {INPUT_PDF}"
    assert sha256(INPUT_PDF) == EXPECTED_INPUT_SHA256, "Unexpected input PDF contents"
    assert os.path.exists(OUTPUT_PDF), f"Missing output file: {OUTPUT_PDF}"

    reader = PdfReader(OUTPUT_PDF)
    assert len(reader.pages) == 6, "Output packet must contain exactly 6 pages"

    page_texts = [normalize(page.extract_text() or "") for page in reader.pages]

    actual_packet_ids = []
    for text in page_texts:
        match = re.search(r"Packet ID:\s*([A-Z0-9-]+)", text)
        assert match, f"Could not find packet ID in page text: {text!r}"
        actual_packet_ids.append(match.group(1))

    assert actual_packet_ids == EXPECTED_PACKET_IDS, (
        f"Unexpected packet order: {actual_packet_ids}"
    )

    for text, snippets in zip(page_texts, EXPECTED_PAGE_SNIPPETS, strict=True):
        for snippet in snippets:
            assert snippet in text, f"Missing expected text {snippet!r} in page {text!r}"

    combined_text = " ".join(page_texts)
    for packet_id in EXCLUDED_PACKET_IDS:
        assert packet_id not in combined_text, f"Found excluded page content: {packet_id}"


if __name__ == "__main__":
    main()
    print("All checks passed.")
