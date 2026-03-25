import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader


OUTPUT_PATH = Path("/root/incident_fields.json")
PDF_PATH = Path("/root/incident_packet/terminal_incident_form.pdf")
PAYLOAD_PATH = Path("/root/incident_packet/response_payload.json")
CONVERT_SCRIPT = Path("/root/.codex/skills/pdf/scripts/convert_pdf_to_images.py")
CHECK_SCRIPT = Path("/root/.codex/skills/pdf/scripts/check_bounding_boxes.py")
FILL_SCRIPT = Path("/root/.codex/skills/pdf/scripts/fill_pdf_form_with_annotations.py")

PDF_WIDTH = 612.0
PDF_HEIGHT = 792.0
TOLERANCE = 12


def pdf_rect_to_image(rect, width, height):
    left, bottom, right, top = rect
    return [
        round(left / PDF_WIDTH * width),
        round((PDF_HEIGHT - top) / PDF_HEIGHT * height),
        round(right / PDF_WIDTH * width),
        round((PDF_HEIGHT - bottom) / PDF_HEIGHT * height),
    ]


def image_rect_to_pdf(rect, width, height):
    left, top, right, bottom = rect
    return [
        left * PDF_WIDTH / width,
        PDF_HEIGHT - bottom * PDF_HEIGHT / height,
        right * PDF_WIDTH / width,
        PDF_HEIGHT - top * PDF_HEIGHT / height,
    ]


def get_expected_specs(payload):
    return {
        "Write the incident ID": {
            "page_number": 1,
            "field_label": "Incident ID",
            "label_rect": [72, 686, 136, 700],
            "entry_rect": [170, 674, 320, 692],
            "text": payload["incident_id"],
        },
        "Write the date of event": {
            "page_number": 1,
            "field_label": "Date of event",
            "label_rect": [72, 642, 153, 656],
            "entry_rect": [170, 630, 270, 648],
            "text": payload["event_date"],
        },
        "Write the reported time": {
            "page_number": 1,
            "field_label": "Time reported",
            "label_rect": [300, 642, 384, 656],
            "entry_rect": [420, 630, 510, 648],
            "text": payload["time_reported"],
        },
        "Write the vehicle and route": {
            "page_number": 1,
            "field_label": "Vehicle / route",
            "label_rect": [84, 580, 170, 596],
            "entry_rect": [190, 566, 528, 598],
            "text": payload["vehicle_route"],
        },
        "Write the intersection or stop": {
            "page_number": 1,
            "field_label": "Intersection / stop",
            "label_rect": [72, 516, 167, 530],
            "entry_rect": [190, 504, 530, 522],
            "text": payload["intersection_stop"],
        },
        "Write the brief event summary": {
            "page_number": 1,
            "field_label": "Brief event summary",
            "label_rect": [72, 474, 177, 488],
            "entry_rect": [84, 392, 528, 438],
            "text": payload["summary"],
        },
        "Mark the No checkbox for medical evaluation needed": {
            "page_number": 2,
            "field_label": "No",
            "label_rect": [380, 654, 397, 668],
            "entry_rect": [406, 650, 422, 666],
            "text": "X",
        },
        "Mark the Yes checkbox for supervisor notified before shift end": {
            "page_number": 2,
            "field_label": "Yes",
            "label_rect": [300, 598, 323, 612],
            "entry_rect": [332, 594, 348, 610],
            "text": "X",
        },
        "Mark the Yes checkbox for photos attached": {
            "page_number": 2,
            "field_label": "Yes",
            "label_rect": [300, 542, 323, 556],
            "entry_rect": [332, 538, 348, 554],
            "text": "X",
        },
        "Write the reviewer name": {
            "page_number": 2,
            "field_label": "Reviewer name",
            "label_rect": [72, 474, 156, 488],
            "entry_rect": [190, 462, 360, 480],
            "text": payload["reviewer_name"],
        },
        "Write the corrective action due date": {
            "page_number": 2,
            "field_label": "Corrective action due",
            "label_rect": [72, 430, 184, 444],
            "entry_rect": [210, 418, 318, 436],
            "text": payload["corrective_action_due"],
        },
    }


def render_images():
    tmp_dir = tempfile.TemporaryDirectory()
    result = subprocess.run(
        [sys.executable, str(CONVERT_SCRIPT), str(PDF_PATH), tmp_dir.name],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    sizes = {}
    for page_number in (1, 2):
        with Image.open(Path(tmp_dir.name) / f"page_{page_number}.png") as image:
            sizes[page_number] = image.size
    return tmp_dir, sizes


def load_output():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"pages", "form_fields"}
    assert isinstance(payload["pages"], list)
    assert isinstance(payload["form_fields"], list)
    return payload


def test_output_schema_and_page_sizes():
    output = load_output()
    tmp_dir, rendered_sizes = render_images()
    try:
        pages = {item["page_number"]: item for item in output["pages"]}
        assert set(pages) == {1, 2}
        for page_number, (width, height) in rendered_sizes.items():
            assert pages[page_number]["image_width"] == width
            assert pages[page_number]["image_height"] == height
    finally:
        tmp_dir.cleanup()


def test_required_fields_and_bounding_boxes_match_layout():
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    expected_specs = get_expected_specs(payload)
    output = load_output()
    tmp_dir, rendered_sizes = render_images()
    try:
        assert len(output["form_fields"]) == len(expected_specs)
        actual_by_description = {item["description"]: item for item in output["form_fields"]}
        assert set(actual_by_description) == set(expected_specs)

        for description, expected in expected_specs.items():
            actual = actual_by_description[description]
            width, height = rendered_sizes[expected["page_number"]]
            assert actual["page_number"] == expected["page_number"]
            assert actual["field_label"] == expected["field_label"]
            assert set(actual["entry_text"]) == {"text", "font_size", "font_color"}
            assert actual["entry_text"]["text"] == expected["text"]
            assert isinstance(actual["entry_text"]["font_size"], int)
            assert actual["entry_text"]["font_color"] == "000000"

            expected_label = pdf_rect_to_image(expected["label_rect"], width, height)
            expected_entry = pdf_rect_to_image(expected["entry_rect"], width, height)
            for got, want in zip(actual["label_bounding_box"], expected_label):
                assert abs(got - want) <= TOLERANCE, (description, "label", actual["label_bounding_box"], expected_label)
            for got, want in zip(actual["entry_bounding_box"], expected_entry):
                assert abs(got - want) <= TOLERANCE, (description, "entry", actual["entry_bounding_box"], expected_entry)
    finally:
        tmp_dir.cleanup()


def test_bounding_box_checker_accepts_output():
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), str(OUTPUT_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "SUCCESS: All bounding boxes are valid" in result.stdout


def test_annotations_can_be_written_to_pdf_in_expected_locations():
    output = load_output()
    pages = {item["page_number"]: item for item in output["pages"]}
    with tempfile.TemporaryDirectory() as tmp_dir:
        annotated_pdf = Path(tmp_dir) / "annotated.pdf"
        result = subprocess.run(
            [sys.executable, str(FILL_SCRIPT), str(PDF_PATH), str(OUTPUT_PATH), str(annotated_pdf)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        reader = PdfReader(str(annotated_pdf))

        annotations_by_page = {}
        for page_index, page in enumerate(reader.pages, start=1):
            raw_annotations = page.get("/Annots") or []
            annotations_by_page[page_index] = [annotation.get_object() for annotation in raw_annotations]

        assert sum(len(items) for items in annotations_by_page.values()) == len(output["form_fields"])

        for field in output["form_fields"]:
            page_number = field["page_number"]
            width = pages[page_number]["image_width"]
            height = pages[page_number]["image_height"]
            expected_rect = image_rect_to_pdf(field["entry_bounding_box"], width, height)
            matching = [
                annotation
                for annotation in annotations_by_page[page_number]
                if annotation.get("/Contents") == field["entry_text"]["text"]
            ]
            assert matching, f"Missing annotation for {field['description']}"
            found = False
            for annotation in matching:
                rect = [float(value) for value in annotation.get("/Rect")]
                if all(abs(a - b) <= 3.0 for a, b in zip(rect, expected_rect)):
                    found = True
                    break
            assert found, f"Annotation rect mismatch for {field['description']}"
