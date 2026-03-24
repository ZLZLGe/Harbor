from pathlib import Path

from pypdf import PdfReader


OUTPUT_FILE = Path("/root/output/exhibit_binder.pdf")
INPUT_DIR = Path("/root/case_files")
EXPECTED_PAGE_COUNT = 14
EXPECTED_TITLE = "Exhibit Binder"
MIN_FILE_SIZE = 250_000

COVER_LINES = [
    "Exhibit Binder",
    "Case: Alder Ridge v. North Basin Logistics",
    "Section 1: Exhibit A - Operations Memo",
    "Section 2: Exhibit B - Email Chain",
    "Section 3: Exhibit C - Billing Backup",
]

EXHIBITS = [
    {
        "label": "Exhibit A - Operations Memo",
        "filename": "exhibit_a_operations_memo.pdf",
        "pages": [2, 3, 4],
    },
    {
        "label": "Exhibit B - Email Chain",
        "filename": "exhibit_b_email_chain.pdf",
        "pages": [1, 2, 5],
    },
    {
        "label": "Exhibit C - Billing Backup",
        "filename": "exhibit_c_billing_backup.pdf",
        "pages": [3, 4, 5, 6],
    },
]


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def canonicalize(text: str) -> str:
    return "".join(ch.lower() for ch in normalize_text(text) if ch.isalnum())


def output_reader() -> PdfReader:
    return PdfReader(str(OUTPUT_FILE))


def expected_output_pages():
    pages = [{"kind": "cover"}]
    for exhibit in EXHIBITS:
        pages.append({"kind": "divider", "label": exhibit["label"]})
        for page_number in exhibit["pages"]:
            pages.append(
                {
                    "kind": "content",
                    "label": exhibit["label"],
                    "filename": exhibit["filename"],
                    "page_number": page_number,
                }
            )
    return pages


def test_output_exists_and_has_nontrivial_size():
    assert OUTPUT_FILE.exists(), "Missing /root/output/exhibit_binder.pdf"
    assert OUTPUT_FILE.stat().st_size > MIN_FILE_SIZE, "Output PDF is unexpectedly small"


def test_metadata_and_page_count():
    reader = output_reader()
    assert len(reader.pages) == EXPECTED_PAGE_COUNT
    metadata = reader.metadata or {}
    assert metadata.get("/Title") == EXPECTED_TITLE


def test_cover_and_divider_pages_present():
    reader = output_reader()

    cover_text = normalize_text(reader.pages[0].extract_text() or "")
    for line in COVER_LINES:
        assert line in cover_text, f"Cover page missing line: {line}"

    expected_pages = expected_output_pages()
    for index, expected in enumerate(expected_pages):
        if expected["kind"] != "divider":
            continue
        divider_text = normalize_text(reader.pages[index].extract_text() or "")
        assert expected["label"] in divider_text, f"Divider page {index + 1} is incorrect"


def test_selected_pages_are_assembled_in_exact_order():
    reader = output_reader()

    for index, expected in enumerate(expected_output_pages()):
        if expected["kind"] != "content":
            continue

        source_reader = PdfReader(str(INPUT_DIR / expected["filename"]))
        source_text = canonicalize(
            source_reader.pages[expected["page_number"] - 1].extract_text() or ""
        )
        output_text = canonicalize(reader.pages[index].extract_text() or "")

        assert len(source_text) > 100, (
            f"Source page {expected['filename']}:{expected['page_number']} "
            "did not yield enough text for comparison"
        )
        assert output_text == source_text, (
            f"Output page {index + 1} does not match "
            f"{expected['filename']} page {expected['page_number']}"
        )


def test_every_output_page_is_upright():
    reader = output_reader()
    rotated_pages = []
    for index, page in enumerate(reader.pages, start=1):
        if (page.rotation or 0) % 360 != 0:
            rotated_pages.append(index)
    assert not rotated_pages, f"Pages still rotated in output: {rotated_pages}"
