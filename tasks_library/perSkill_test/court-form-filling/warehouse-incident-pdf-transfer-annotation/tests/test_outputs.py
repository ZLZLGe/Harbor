import subprocess
from pathlib import Path

import pytest
from PIL import Image

INPUT_FILE = Path("/root/warehouse-incident-report.pdf")
OUTPUT_FILE = Path("/root/incident-report-completed.pdf")
PDF_WIDTH = 612
PDF_HEIGHT = 792

EXPECTED_TEXT = [
    "Daniel Ruiz",
    "Forklift Operator",
    "Zone 3",
    "2026-02-14",
    "07:35",
    "08:10",
    "Backing pallet jack clipped rack B-17",
    "area cordoned off for inspection.",
]

CHECKED_BOXES = {
    "injury_no": (315, 515, 18, 18),
    "equipment_damage_yes": (230, 470, 18, 18),
    "witness_yes": (230, 425, 18, 18),
}

UNCHECKED_BOXES = {
    "injury_yes": (230, 515, 18, 18),
    "equipment_damage_no": (315, 470, 18, 18),
    "witness_no": (315, 425, 18, 18),
}

BLANK_SECTION_RECT = (72, 170, 468, 60)


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        pytest.fail(f"Command failed: {' '.join(command)}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def extract_pdf_text(pdf_path: Path) -> str:
    return run_command(["pdftotext", "-layout", str(pdf_path), "-"]).stdout


def render_pdf_page(pdf_path: Path, prefix: str) -> Image.Image:
    output_prefix = f"/tmp/{prefix}"
    run_command(["pdftoppm", "-png", "-r", "200", "-f", "1", "-singlefile", str(pdf_path), output_prefix])
    image_path = Path(output_prefix + ".png")
    if not image_path.exists():
        pytest.fail(f"Rendered image not found at {image_path}")
    return Image.open(image_path).convert("L")


def crop_pdf_rect(image: Image.Image, rect):
    x, y, width, height = rect
    left = int(x / PDF_WIDTH * image.width)
    right = int((x + width) / PDF_WIDTH * image.width)
    top = int((PDF_HEIGHT - (y + height)) / PDF_HEIGHT * image.height)
    bottom = int((PDF_HEIGHT - y) / PDF_HEIGHT * image.height)
    return image.crop((left, top, right, bottom))


def changed_pixels(blank_crop: Image.Image, filled_crop: Image.Image) -> int:
    changes = 0
    for blank_value, filled_value in zip(blank_crop.getdata(), filled_crop.getdata()):
        if blank_value - filled_value > 35:
            changes += 1
    return changes


@pytest.fixture(scope="module")
def output_text():
    if not OUTPUT_FILE.exists():
        pytest.fail(f"Output file not found at {OUTPUT_FILE}")
    return extract_pdf_text(OUTPUT_FILE)


@pytest.fixture(scope="module")
def rendered_pages():
    if not INPUT_FILE.exists():
        pytest.fail(f"Input file not found at {INPUT_FILE}")
    if not OUTPUT_FILE.exists():
        pytest.fail(f"Output file not found at {OUTPUT_FILE}")
    return {
        "blank": render_pdf_page(INPUT_FILE, "incident_blank"),
        "filled": render_pdf_page(OUTPUT_FILE, "incident_filled"),
    }


class TestOutputFile:
    def test_output_exists_and_is_pdf(self):
        assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"
        with open(OUTPUT_FILE, "rb") as handle:
            assert handle.read(5) == b"%PDF-", "Output file is not a valid PDF"

    def test_output_differs_from_input(self):
        assert INPUT_FILE.exists(), f"Input file not found at {INPUT_FILE}"
        assert OUTPUT_FILE.read_bytes() != INPUT_FILE.read_bytes(), "Output PDF should differ from the blank report"


class TestRequiredText:
    @pytest.mark.parametrize("expected_text", EXPECTED_TEXT)
    def test_expected_text_present(self, output_text, expected_text):
        assert expected_text in output_text, f"Expected text not found: {expected_text!r}"


class TestCheckboxMarks:
    @pytest.mark.parametrize("name,rect", CHECKED_BOXES.items(), ids=CHECKED_BOXES.keys())
    def test_expected_box_checked(self, rendered_pages, name, rect):
        blank_crop = crop_pdf_rect(rendered_pages["blank"], rect)
        filled_crop = crop_pdf_rect(rendered_pages["filled"], rect)
        assert changed_pixels(blank_crop, filled_crop) > 180, f"Expected checkbox mark missing for {name}"

    @pytest.mark.parametrize("name,rect", UNCHECKED_BOXES.items(), ids=UNCHECKED_BOXES.keys())
    def test_other_box_unchecked(self, rendered_pages, name, rect):
        blank_crop = crop_pdf_rect(rendered_pages["blank"], rect)
        filled_crop = crop_pdf_rect(rendered_pages["filled"], rect)
        assert changed_pixels(blank_crop, filled_crop) < 80, f"Unexpected checkbox mark found for {name}"

    def test_supervisor_notes_area_left_blank(self, rendered_pages):
        blank_crop = crop_pdf_rect(rendered_pages["blank"], BLANK_SECTION_RECT)
        filled_crop = crop_pdf_rect(rendered_pages["filled"], BLANK_SECTION_RECT)
        assert changed_pixels(blank_crop, filled_crop) < 120, "Supervisor notes area should remain blank"
