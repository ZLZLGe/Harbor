import os
from pathlib import Path

from pypdf import PdfReader


OUTPUT_PATH = Path("/root/completed_enrollment_packet.pdf")
RECT_TOLERANCE = 2.0

EXPECTED_FIELDS = {
    "legal_name": "Elena Sofiya Petrov",
    "preferred_name": "Elena Petrov",
    "date_of_birth": "09/28/2004",
    "student_id": "TR-618204",
    "program_name": "M.S. in Human-Centered Design",
    "start_term": "Spring 2027",
    "email": "elena.petrov@example.edu",
    "mobile_phone": "(312) 555-0184",
    "typed_signature": "Elena Sofiya Petrov",
    "completion_date": "03/18/2026",
}

EXPECTED_TEXT_ANNOTATIONS = {
    2: [
        ("85 Queens Quay W Unit 1204", [160, 620, 520, 638]),
        ("Toronto / ON / M5J 2Y2 / Canada", [160, 590, 520, 608]),
        ("Irina Petrov", [72, 518, 270, 534]),
        ("Mother", [300, 518, 420, 534]),
        ("+1-647-555-0199", [72, 478, 270, 494]),
    ],
    3: [
        ("Lakeshore College", [210, 630, 528, 646]),
        ("18", [250, 590, 350, 606]),
        ("Requires captioning support during orientation presentations.", [84, 320, 528, 350]),
    ],
}

EXPECTED_X_RECTS = {
    2: [
        [228, 430, 244, 446],
        [88, 358, 104, 374],
        [88, 328, 104, 344],
    ],
    3: [
        [88, 538, 104, 554],
        [228, 468, 244, 484],
    ],
    4: [
        [218, 638, 234, 654],
        [88, 578, 104, 594],
        [88, 498, 104, 514],
    ],
}


def _rect_close(actual, expected):
    return all(abs(float(a) - float(e)) <= RECT_TOLERANCE for a, e in zip(actual, expected))


def _freetext_annotations(page):
    annotations = []
    for annot_ref in page.get("/Annots", []) or []:
        annot = annot_ref.get_object()
        if str(annot.get("/Subtype")) != "/FreeText":
            continue
        annotations.append(
            {
                "text": str(annot.get("/Contents", "")),
                "rect": [float(value) for value in annot.get("/Rect", [])],
            }
        )
    return annotations


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists(OUTPUT_PATH)

    def test_page_count_and_form_values(self):
        reader = PdfReader(str(OUTPUT_PATH))
        assert len(reader.pages) == 4, "The completed packet must preserve all 4 pages."

        fields = reader.get_fields()
        assert fields, "The output must keep the built-in form fields on pages 1 and 4."

        for field_name, expected_value in EXPECTED_FIELDS.items():
            assert field_name in fields, f"Missing expected form field: {field_name}"
            actual_value = fields[field_name].get("/V")
            assert str(actual_value) == expected_value, (
                f"Incorrect value for {field_name}: expected {expected_value!r}, got {actual_value!r}"
            )

    def test_text_annotations(self):
        reader = PdfReader(str(OUTPUT_PATH))

        for page_number, expected_entries in EXPECTED_TEXT_ANNOTATIONS.items():
            annotations = _freetext_annotations(reader.pages[page_number - 1])
            for expected_text, expected_rect in expected_entries:
                assert any(
                    annotation["text"] == expected_text and _rect_close(annotation["rect"], expected_rect)
                    for annotation in annotations
                ), f"Missing annotation {expected_text!r} on page {page_number} in the expected region."

    def test_checkbox_marks(self):
        reader = PdfReader(str(OUTPUT_PATH))

        for page_number, expected_rects in EXPECTED_X_RECTS.items():
            annotations = _freetext_annotations(reader.pages[page_number - 1])
            actual_x_rects = [annotation["rect"] for annotation in annotations if annotation["text"] == "X"]
            assert len(actual_x_rects) == len(expected_rects), (
                f"Page {page_number} should contain {len(expected_rects)} checkbox marks, "
                f"found {len(actual_x_rects)}."
            )
            for expected_rect in expected_rects:
                assert any(_rect_close(actual_rect, expected_rect) for actual_rect in actual_x_rects), (
                    f"Missing checkbox mark on page {page_number} at {expected_rect}."
                )
