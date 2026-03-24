#!/bin/bash
set -euo pipefail

python3 /root/.codex/skills/pdf/scripts/extract_form_field_info.py \
  /root/enrollment_packet_template.pdf \
  /tmp/enrollment_field_info.json

python3 <<'PY'
import json
from datetime import datetime
from pathlib import Path

PAGE_WIDTH = 612
PAGE_HEIGHT = 792


def mmddyyyy(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%m/%d/%Y")


def to_image_bbox(left: int, bottom: int, right: int, top: int) -> list[int]:
    return [left, PAGE_HEIGHT - top, right, PAGE_HEIGHT - bottom]


profile = json.loads(Path("/root/applicant_profile.json").read_text(encoding="utf-8"))
field_info = json.loads(Path("/tmp/enrollment_field_info.json").read_text(encoding="utf-8"))
field_by_id = {entry["field_id"]: entry for entry in field_info}

fillable_values = {
    "legal_name": profile["legal_name"],
    "preferred_name": profile["preferred_name"],
    "date_of_birth": mmddyyyy(profile["date_of_birth"]),
    "student_id": profile["student_id"],
    "program_name": profile["program_name"],
    "start_term": profile["start_term"],
    "email": profile["email"],
    "mobile_phone": profile["mobile_phone"],
    "typed_signature": profile["typed_signature"],
    "completion_date": mmddyyyy(profile["completion_date"]),
}

missing_fields = sorted(set(fillable_values) - set(field_by_id))
if missing_fields:
    raise SystemExit(f"Missing expected form fields: {missing_fields}")

field_values = [
    {
        "field_id": field_id,
        "description": f"Filled from applicant_profile.json: {field_id}",
        "page": field_by_id[field_id]["page"],
        "value": value,
    }
    for field_id, value in fillable_values.items()
]

Path("/tmp/fill_values.json").write_text(
    json.dumps(field_values, indent=2),
    encoding="utf-8",
)

address = profile["mailing_address"]
emergency = profile["emergency_contact"]
preferences = profile["communication_preferences"]

annotation_fields = {
    "pages": [
        {"page_number": 1, "image_width": PAGE_WIDTH, "image_height": PAGE_HEIGHT},
        {"page_number": 2, "image_width": PAGE_WIDTH, "image_height": PAGE_HEIGHT},
        {"page_number": 3, "image_width": PAGE_WIDTH, "image_height": PAGE_HEIGHT},
        {"page_number": 4, "image_width": PAGE_WIDTH, "image_height": PAGE_HEIGHT},
    ],
    "form_fields": [
        {
            "page_number": 2,
            "description": "Street or unit line",
            "entry_bounding_box": to_image_bbox(160, 620, 520, 638),
            "entry_text": {"text": address["line1"], "font_size": 11},
        },
        {
            "page_number": 2,
            "description": "City, region, postal code, and country line",
            "entry_bounding_box": to_image_bbox(160, 590, 520, 608),
            "entry_text": {
                "text": f'{address["city"]} / {address["region"]} / {address["postal_code"]} / {address["country"]}',
                "font_size": 11,
            },
        },
        {
            "page_number": 2,
            "description": "Emergency contact name",
            "entry_bounding_box": to_image_bbox(72, 518, 270, 534),
            "entry_text": {"text": emergency["name"], "font_size": 11},
        },
        {
            "page_number": 2,
            "description": "Emergency contact relationship",
            "entry_bounding_box": to_image_bbox(300, 518, 420, 534),
            "entry_text": {"text": emergency["relationship"], "font_size": 11},
        },
        {
            "page_number": 2,
            "description": "Emergency contact phone",
            "entry_bounding_box": to_image_bbox(72, 478, 270, 494),
            "entry_text": {"text": emergency["phone"], "font_size": 11},
        },
        {
            "page_number": 3,
            "description": "Previous institution",
            "entry_bounding_box": to_image_bbox(210, 630, 528, 646),
            "entry_text": {"text": profile["previous_institution"], "font_size": 11},
        },
        {
            "page_number": 3,
            "description": "Accepted transfer credits",
            "entry_bounding_box": to_image_bbox(250, 590, 350, 606),
            "entry_text": {"text": str(profile["transfer_credits_accepted"]), "font_size": 11},
        },
        {
            "page_number": 3,
            "description": "Support note",
            "entry_bounding_box": to_image_bbox(84, 320, 528, 350),
            "entry_text": {"text": profile["support_note"], "font_size": 11},
        },
    ],
}

checkbox_targets = [
    (
        2,
        "Residency status",
        to_image_bbox(228, 430, 244, 446)
        if profile["citizenship"] == "International"
        else to_image_bbox(88, 430, 104, 446),
    ),
    (
        3,
        "Attendance mode",
        to_image_bbox(88, 538, 104, 554)
        if profile["attendance_mode"] == "Full-Time"
        else to_image_bbox(218, 538, 234, 554),
    ),
    (
        3,
        "Housing plan",
        {
            "On-Campus": to_image_bbox(88, 468, 104, 484),
            "Off-Campus": to_image_bbox(228, 468, 244, 484),
            "Commuter": to_image_bbox(378, 468, 394, 484),
        }[profile["housing_plan"]],
    ),
    (
        4,
        "Directory listing preference",
        to_image_bbox(88, 638, 104, 654)
        if preferences["directory_opt_in"]
        else to_image_bbox(218, 638, 234, 654),
    ),
    (
        4,
        "SMS alerts preference",
        to_image_bbox(88, 578, 104, 594)
        if preferences["sms_alerts"]
        else to_image_bbox(218, 578, 234, 594),
    ),
]

for option in profile["orientation_addons"]:
    orientation_boxes = {
        "Airport Shuttle": to_image_bbox(88, 358, 104, 374),
        "Early Housing Tour": to_image_bbox(88, 328, 104, 344),
        "Meal Plan Waiver": to_image_bbox(88, 298, 104, 314),
    }
    checkbox_targets.append((2, f"Orientation add-on: {option}", orientation_boxes[option]))

if profile["financial_terms_accepted"]:
    checkbox_targets.append((4, "Financial terms acknowledgement", to_image_bbox(88, 498, 104, 514)))

for page_number, description, bbox in checkbox_targets:
    annotation_fields["form_fields"].append(
        {
            "page_number": page_number,
            "description": description,
            "entry_bounding_box": bbox,
            "entry_text": {"text": "X", "font_size": 12},
        }
    )

Path("/tmp/annotation_fields.json").write_text(
    json.dumps(annotation_fields, indent=2),
    encoding="utf-8",
)
PY

python3 /root/.codex/skills/pdf/scripts/fill_fillable_fields.py \
  /root/enrollment_packet_template.pdf \
  /tmp/fill_values.json \
  /tmp/enrollment_fillable.pdf

python3 /root/.codex/skills/pdf/scripts/fill_pdf_form_with_annotations.py \
  /tmp/enrollment_fillable.pdf \
  /tmp/annotation_fields.json \
  /root/completed_enrollment_packet.pdf
