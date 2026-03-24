import csv
import os

from pypdf import PdfReader


OUTPUT_FILE = "/app/workspace/audit_review_packet.pdf"
PLAN_FILE = "/app/workspace/audit_packet_plan.csv"

EXPECTED_PAGE_CODES = [
    "Document Code: BM-02",
    "Document Code: EL-02",
    "Document Code: ES-04",
    "Document Code: CW-01",
    "Document Code: ES-02",
    "Document Code: EL-03",
    "Document Code: CW-03",
]

EXPECTED_SOURCE_MARKERS = [
    "SRC board_minutes_extract.pdf | PAGE 2 | Budget Sign-off Appendix",
    "SRC engagement_letter.pdf | PAGE 2 | Signed Engagement Approval",
    "SRC expense_support.pdf | PAGE 4 | Meal Receipt Index",
    "SRC control_walkthrough.pdf | PAGE 1 | Control Walkthrough Agenda",
    "SRC expense_support.pdf | PAGE 2 | Hotel Folio Extract",
    "SRC engagement_letter.pdf | PAGE 3 | Billing Terms Addendum",
    "SRC control_walkthrough.pdf | PAGE 3 | Remediation Status Memo",
]


def normalize_rotation(value):
    if value is None:
        return 0
    return int(value) % 360


def load_plan_rows():
    with open(PLAN_FILE, "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return sorted(rows, key=lambda row: int(row["packet_order"]))


def test_output_exists():
    assert os.path.exists(OUTPUT_FILE), "audit_review_packet.pdf not found at /app/workspace"


def test_pdf_page_order_and_rotation():
    plan_rows = load_plan_rows()
    reader = PdfReader(OUTPUT_FILE)

    assert len(reader.pages) == len(plan_rows), (
        "Output page count must match audit_packet_plan.csv.\n"
        f"Actual: {len(reader.pages)}\n"
        f"Expected: {len(plan_rows)}"
    )

    extracted_markers = []
    extracted_codes = []

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        extracted_markers.append(next((marker for marker in EXPECTED_SOURCE_MARKERS if marker in text), None))
        extracted_codes.append(next((code for code in EXPECTED_PAGE_CODES if code in text), None))

        assert normalize_rotation(page.get("/Rotate")) == 0, (
            f"Output page {index + 1} still has non-zero rotation metadata: {page.get('/Rotate')}"
        )

    assert extracted_markers == EXPECTED_SOURCE_MARKERS, (
        "Output pages are not assembled from the expected source pages in the correct order.\n"
        f"Actual: {extracted_markers}\n"
        f"Expected: {EXPECTED_SOURCE_MARKERS}"
    )

    assert extracted_codes == EXPECTED_PAGE_CODES, (
        "Document codes in the merged packet do not match the plan order.\n"
        f"Actual: {extracted_codes}\n"
        f"Expected: {EXPECTED_PAGE_CODES}"
    )


def test_plan_file_shape():
    rows = load_plan_rows()
    assert rows, "audit_packet_plan.csv must not be empty"
    assert [int(row["packet_order"]) for row in rows] == list(range(1, len(rows) + 1)), (
        "packet_order must be a continuous sequence starting from 1."
    )

    for row in rows:
        assert set(row.keys()) == {
            "packet_order",
            "source_pdf",
            "page_number",
            "rotate_clockwise",
            "document_code",
            "section_title",
        }, f"Unexpected plan columns: {row.keys()}"
