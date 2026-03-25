#!/bin/bash
set -euo pipefail

PAGES_DIR=/tmp/incident_pages
mkdir -p "$PAGES_DIR"

python3 /root/.codex/skills/pdf/scripts/convert_pdf_to_images.py \
  /root/incident_packet/terminal_incident_form.pdf \
  "$PAGES_DIR"

python3 - <<'PY'
import json
from pathlib import Path

from PIL import Image


PDF_WIDTH = 612.0
PDF_HEIGHT = 792.0
PAGES_DIR = Path("/tmp/incident_pages")
PAYLOAD_PATH = Path("/root/incident_packet/response_payload.json")
OUTPUT_PATH = Path("/root/incident_fields.json")


def pdf_rect_to_image(rect, width, height):
    left, bottom, right, top = rect
    return [
        round(left / PDF_WIDTH * width),
        round((PDF_HEIGHT - top) / PDF_HEIGHT * height),
        round(right / PDF_WIDTH * width),
        round((PDF_HEIGHT - bottom) / PDF_HEIGHT * height),
    ]


payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))

page_sizes = {}
pages = []
for page_number in (1, 2):
    with Image.open(PAGES_DIR / f"page_{page_number}.png") as image:
        width, height = image.size
    page_sizes[page_number] = (width, height)
    pages.append(
        {
            "page_number": page_number,
            "image_width": width,
            "image_height": height,
        }
    )

specs = [
    {
        "page_number": 1,
        "description": "Write the incident ID",
        "field_label": "Incident ID",
        "label_rect": [72, 686, 136, 700],
        "entry_rect": [170, 674, 320, 692],
        "text": payload["incident_id"],
    },
    {
        "page_number": 1,
        "description": "Write the date of event",
        "field_label": "Date of event",
        "label_rect": [72, 642, 153, 656],
        "entry_rect": [170, 630, 270, 648],
        "text": payload["event_date"],
    },
    {
        "page_number": 1,
        "description": "Write the reported time",
        "field_label": "Time reported",
        "label_rect": [300, 642, 384, 656],
        "entry_rect": [420, 630, 510, 648],
        "text": payload["time_reported"],
    },
    {
        "page_number": 1,
        "description": "Write the vehicle and route",
        "field_label": "Vehicle / route",
        "label_rect": [84, 580, 170, 596],
        "entry_rect": [190, 566, 528, 598],
        "text": payload["vehicle_route"],
    },
    {
        "page_number": 1,
        "description": "Write the intersection or stop",
        "field_label": "Intersection / stop",
        "label_rect": [72, 516, 167, 530],
        "entry_rect": [190, 504, 530, 522],
        "text": payload["intersection_stop"],
    },
    {
        "page_number": 1,
        "description": "Write the brief event summary",
        "field_label": "Brief event summary",
        "label_rect": [72, 474, 177, 488],
        "entry_rect": [84, 392, 528, 438],
        "text": payload["summary"],
    },
    {
        "page_number": 2,
        "description": "Mark the No checkbox for medical evaluation needed",
        "field_label": "No",
        "label_rect": [380, 654, 397, 668],
        "entry_rect": [406, 650, 422, 666],
        "text": "X",
    },
    {
        "page_number": 2,
        "description": "Mark the Yes checkbox for supervisor notified before shift end",
        "field_label": "Yes",
        "label_rect": [300, 598, 323, 612],
        "entry_rect": [332, 594, 348, 610],
        "text": "X",
    },
    {
        "page_number": 2,
        "description": "Mark the Yes checkbox for photos attached",
        "field_label": "Yes",
        "label_rect": [300, 542, 323, 556],
        "entry_rect": [332, 538, 348, 554],
        "text": "X",
    },
    {
        "page_number": 2,
        "description": "Write the reviewer name",
        "field_label": "Reviewer name",
        "label_rect": [72, 474, 156, 488],
        "entry_rect": [190, 462, 360, 480],
        "text": payload["reviewer_name"],
    },
    {
        "page_number": 2,
        "description": "Write the corrective action due date",
        "field_label": "Corrective action due",
        "label_rect": [72, 430, 184, 444],
        "entry_rect": [210, 418, 318, 436],
        "text": payload["corrective_action_due"],
    },
]

form_fields = []
for spec in specs:
    width, height = page_sizes[spec["page_number"]]
    form_fields.append(
        {
            "page_number": spec["page_number"],
            "description": spec["description"],
            "field_label": spec["field_label"],
            "label_bounding_box": pdf_rect_to_image(spec["label_rect"], width, height),
            "entry_bounding_box": pdf_rect_to_image(spec["entry_rect"], width, height),
            "entry_text": {
                "text": spec["text"],
                "font_size": 14,
                "font_color": "000000",
            },
        }
    )

OUTPUT_PATH.write_text(
    json.dumps({"pages": pages, "form_fields": form_fields}, indent=2),
    encoding="utf-8",
)
PY

python3 /root/.codex/skills/pdf/scripts/check_bounding_boxes.py /root/incident_fields.json
