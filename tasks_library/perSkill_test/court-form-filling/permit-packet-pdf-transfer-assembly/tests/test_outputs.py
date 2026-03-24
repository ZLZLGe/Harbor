from pathlib import Path

from pypdf import PdfReader

OUTPUT_FILE = Path("/root/permit-submission-packet.pdf")

EXPECTED_PAGE_MARKERS = [
    ("Permit Application Packet", "APP-02 Project Details"),
    ("Permit Application Packet", "APP-01 Cover Sheet"),
    ("Site Inspection Record", "INS-03 Photo Log Index"),
    ("Site Inspection Record", "INS-01 Initial Inspection Summary"),
    ("Structural Attachments", "ATT-02 Engineering Sign-Off"),
]

EXCLUDED_MARKERS = [
    "APP-03 Applicant Instructions",
    "APP-04 Filing Checklist",
    "INS-02 Inspector Notes",
    "ATT-01 Calculation Backup",
    "ATT-03 Reference Diagram",
]


def normalize(text: str) -> str:
    return " ".join(text.split())


def read_output_pages() -> list[str]:
    reader = PdfReader(str(OUTPUT_FILE))
    return [normalize(page.extract_text() or "") for page in reader.pages]


def test_output_exists() -> None:
    assert OUTPUT_FILE.exists(), "Missing /root/permit-submission-packet.pdf"


def test_output_has_expected_pages_in_order() -> None:
    pages = read_output_pages()
    assert len(pages) == len(EXPECTED_PAGE_MARKERS), (
        f"Expected {len(EXPECTED_PAGE_MARKERS)} pages, found {len(pages)}"
    )

    for page_text, expected_markers in zip(pages, EXPECTED_PAGE_MARKERS):
        for marker in expected_markers:
            assert marker in page_text, f"Missing marker {marker!r} on page text: {page_text!r}"


def test_output_does_not_include_excluded_pages() -> None:
    combined_text = " ".join(read_output_pages())
    for marker in EXCLUDED_MARKERS:
        assert marker not in combined_text, f"Excluded page marker {marker!r} found in output"
