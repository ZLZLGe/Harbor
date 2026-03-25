#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText


INPUT_PATH = Path("/root/inspection_form.pdf")
ANSWERS_PATH = Path("/root/inspection_answers.json")
OUTPUT_PATH = Path("/root/annotated_inspection_form.pdf")


def add_annotation(writer, page_number, rect, text, font_size=12):
    writer.add_annotation(
        page_number=page_number - 1,
        annotation=FreeText(
            text=text,
            rect=rect,
            font="Helvetica",
            font_size=f"{font_size}pt",
            font_color="000000",
            border_color=None,
            background_color=None,
        ),
    )


answers = json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))
reader = PdfReader(str(INPUT_PATH))
writer = PdfWriter()
writer.append(reader)

text_fields = [
    (1, [124, 646, 320, 668], answers["site_name"], 12),
    (1, [458, 646, 546, 668], answers["inspection_date"], 11),
    (1, [114, 606, 258, 628], answers["inspector"], 12),
    (1, [370, 606, 498, 628], answers["permit_number"], 12),
    (1, [154, 406, 278, 428], answers["pump_station_id"], 12),
    (1, [410, 406, 470, 428], str(answers["pressure_psi"]), 12),
    (2, [66, 560, 544, 592], answers["action_notes"], 11),
]

for page_number, rect, value, font_size in text_fields:
    add_annotation(writer, page_number, rect, value, font_size)

checkboxes = []
shift_choice = answers["shift"].strip().lower()
checkboxes.append((1, [139, 567, 151, 579], "X") if shift_choice == "day" else (1, [229, 567, 241, 579], "X"))

weather_choice = answers["weather"].strip().lower()
weather_rects = {
    "clear": [402, 567, 414, 579],
    "rain": [479, 567, 491, 579],
    "windy": [553, 567, 565, 579],
}
checkboxes.append((1, weather_rects[weather_choice], "X"))

boolean_rects = {
    "safety_briefing_completed": ([228, 527, 240, 539], [294, 527, 306, 539]),
    "access_gate_secure": ([194, 487, 206, 499], [260, 487, 272, 499]),
    "fire_extinguishers_visible": ([480, 487, 492, 499], [546, 487, 558, 499]),
    "spill_kit_stocked": ([180, 379, 192, 391], [246, 379, 258, 391]),
    "trip_hazards_observed": ([472, 379, 484, 391], [538, 379, 550, 391]),
    "follow_up_required": ([190, 665, 202, 677], [256, 665, 268, 677]),
}

for key, (yes_rect, no_rect) in boolean_rects.items():
    selected_rect = yes_rect if answers["checks"][key] else no_rect
    checkboxes.append((1 if key != "follow_up_required" else 2, selected_rect, "X"))

for page_number, rect, value in checkboxes:
    add_annotation(writer, page_number, rect, value, 12)

with OUTPUT_PATH.open("wb") as fh:
    writer.write(fh)
PY
