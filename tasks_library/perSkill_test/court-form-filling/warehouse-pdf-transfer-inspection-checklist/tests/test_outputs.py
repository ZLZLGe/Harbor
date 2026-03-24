import subprocess
import tempfile
from pathlib import Path

import pdfplumber
from PIL import Image
from pypdf import PdfReader


OUTPUT_FILE = Path("/root/warehouse-inspection-completed.pdf")
INPUT_FILE = Path("/root/warehouse-inspection-checklist.pdf")

PAGE_HEIGHT = 792
CHECKBOX_SIZE = 14
SCALE = 2

TEXT_EXPECTATIONS = [
    (1, (96, 68, 340, 96), "North Harbor Fulfillment Center"),
    (1, (450, 68, 560, 96), "2026-02-18"),
    (1, (72, 98, 170, 126), "Evening"),
    (1, (244, 98, 420, 126), "Nora Patel"),
    (1, (72, 128, 560, 156), "Dock 3 / Cold Storage Corridor"),
    (2, (40, 92, 560, 208), "Pallet was blocking the forklift charging lane at Dock 3."),
    (2, (40, 252, 560, 338), "Removed pallet immediately and placed a caution cone until repainting."),
    (2, (40, 382, 560, 468), "Submit ticket MX-2047 and verify lane striping by 2026-02-19."),
    (2, (132, 486, 250, 514), "MX-2047"),
    (2, (404, 486, 560, 514), "2026-02-18 19:40"),
    (2, (146, 526, 290, 554), "2026-02-19"),
    (2, (438, 526, 520, 554), "RL"),
    (2, (142, 611, 330, 639), "Nora Patel"),
]

BLANK_TEXT_REGIONS = [
    (2, (476, 611, 560, 639)),
    (2, (116, 651, 250, 679)),
]

CHECKED_BOXES = {
    "row_1_pass": (1, 432, 543),
    "row_2_action": (1, 502, 505),
    "row_3_pass": (1, 432, 467),
    "row_4_pass": (1, 432, 429),
    "row_5_pass": (1, 432, 391),
    "follow_up_yes": (1, 150, 343),
    "hazard_yes": (1, 454, 343),
    "reinspection_yes": (2, 158, 209),
}

UNCHECKED_BOXES = {
    "row_1_action": (1, 502, 543),
    "row_2_pass": (1, 432, 505),
    "row_3_action": (1, 502, 467),
    "row_4_action": (1, 502, 429),
    "row_5_action": (1, 502, 391),
    "follow_up_no": (1, 215, 343),
    "hazard_no": (1, 520, 343),
    "reinspection_no": (2, 223, 209),
}


def crop_text(page, bbox):
    region = page.crop(bbox)
    text = region.extract_text() or ""
    return " ".join(text.split())


def render_pages(pdf_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        prefix = Path(tmpdir) / "page"
        subprocess.run(
            ["pdftoppm", "-png", "-r", "144", str(pdf_path), str(prefix)],
            check=True,
            capture_output=True,
            text=True,
        )
        images = []
        for image_path in sorted(Path(tmpdir).glob("page-*.png")):
            images.append(Image.open(image_path).convert("L"))
        return images


def inner_dark_pixel_count(image, pdf_x, pdf_y, size=CHECKBOX_SIZE):
    image_x0 = int((pdf_x + 3) * SCALE)
    image_x1 = int((pdf_x + size - 3) * SCALE)
    image_y0 = int((PAGE_HEIGHT - (pdf_y + size - 3)) * SCALE)
    image_y1 = int((PAGE_HEIGHT - (pdf_y + 3)) * SCALE)
    region = image.crop((image_x0, image_y0, image_x1, image_y1))
    pixels = list(region.getdata())
    return sum(1 for value in pixels if value < 180)


def test_output_exists_and_input_is_non_fillable():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    assert INPUT_FILE.exists(), f"Missing input file: {INPUT_FILE}"
    assert OUTPUT_FILE.read_bytes().startswith(b"%PDF-")
    assert OUTPUT_FILE.read_bytes() != INPUT_FILE.read_bytes(), "Output PDF should differ from the blank checklist"

    reader = PdfReader(str(INPUT_FILE))
    assert len(reader.pages) == 2
    assert not reader.get_fields(), "Input checklist should be non-fillable"


def test_text_is_written_into_expected_regions():
    with pdfplumber.open(str(OUTPUT_FILE)) as pdf:
        for page_number, bbox, expected_text in TEXT_EXPECTATIONS:
            page = pdf.pages[page_number - 1]
            actual = crop_text(page, bbox)
            assert expected_text in actual, f"Expected {expected_text!r} in page {page_number} bbox {bbox}, got {actual!r}"


def test_optional_review_fields_stay_blank():
    with pdfplumber.open(str(OUTPUT_FILE)) as pdf:
        for page_number, bbox in BLANK_TEXT_REGIONS:
            page = pdf.pages[page_number - 1]
            actual = crop_text(page, bbox)
            assert actual == "", f"Expected blank region on page {page_number} bbox {bbox}, got {actual!r}"


def test_checkbox_marks_match_the_record():
    images = render_pages(OUTPUT_FILE)

    for name, (page_number, x, y) in CHECKED_BOXES.items():
        dark_pixels = inner_dark_pixel_count(images[page_number - 1], x, y)
        assert dark_pixels >= 18, f"{name} should be marked, dark pixel count was {dark_pixels}"

    for name, (page_number, x, y) in UNCHECKED_BOXES.items():
        dark_pixels = inner_dark_pixel_count(images[page_number - 1], x, y)
        assert dark_pixels <= 8, f"{name} should be blank, dark pixel count was {dark_pixels}"
