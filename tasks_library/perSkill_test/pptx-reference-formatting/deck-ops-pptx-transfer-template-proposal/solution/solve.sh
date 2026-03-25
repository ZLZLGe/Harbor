#!/bin/bash
set -euo pipefail

python3 /root/.codex/skills/pptx/scripts/rearrange.py \
  /root/GreenGrid-Template-Workbook.pptx \
  /root/GreenGrid-Proposal-tailored.pptx \
  0,2,3,4,6,7

python3 <<'PY'
from __future__ import annotations

from pathlib import Path

import yaml
from pptx import Presentation

BRIEF_PATH = Path("/root/proposal_brief.yaml")
OUTPUT_PATH = Path("/root/GreenGrid-Proposal-tailored.pptx")
ASSETS_DIR = Path("/root/proposal-assets")


def load_brief() -> dict:
    return yaml.safe_load(BRIEF_PATH.read_text(encoding="utf-8"))


def set_paragraph_text(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.text = text


def replace_tokens(prs: Presentation, mapping: dict[str, str]) -> None:
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for paragraph in shape.text_frame.paragraphs:
                current = "".join(run.text for run in paragraph.runs) if paragraph.runs else paragraph.text
                if current in mapping:
                    set_paragraph_text(paragraph, mapping[current])


def replace_picture(slide, slot_name: str, image_path: Path) -> None:
    for shape in slide.shapes:
        if getattr(shape, "name", "") != slot_name:
            continue
        left, top, width, height = shape.left, shape.top, shape.width, shape.height
        sp = shape._element
        sp.getparent().remove(sp)
        slide.shapes.add_picture(str(image_path), left, top, width=width, height=height)
        return
    raise RuntimeError(f"missing picture slot: {slot_name}")


brief = load_brief()
prs = Presentation(OUTPUT_PATH)

token_map = {
    "{{COVER_KICKER}}": brief["cover"]["kicker"],
    "{{COVER_TITLE}}": brief["cover"]["title"],
    "{{COVER_SUBTITLE}}": brief["cover"]["subtitle"],
    "{{COVER_TAGLINE}}": brief["cover"]["tagline"],
    "[replace with client-ready cover image]": "",
    "{{OPPORTUNITY_TITLE}}": brief["opportunity"]["title"],
    "{{OPPORTUNITY_INTRO}}": brief["opportunity"]["intro"],
    "{{OPPORTUNITY_POINT_1}}": brief["opportunity"]["bullets"][0],
    "{{OPPORTUNITY_POINT_2}}": brief["opportunity"]["bullets"][1],
    "{{OPPORTUNITY_STAT_LABEL}}": brief["opportunity"]["stat_label"],
    "{{OPPORTUNITY_STAT_VALUE}}": brief["opportunity"]["stat_value"],
    "[replace with opportunity image]": "",
    "{{SOLUTION_TITLE}}": brief["solution"]["title"],
    "{{SOLUTION_INTRO}}": brief["solution"]["intro"],
    "{{SOLUTION_PILLAR_1}}": brief["solution"]["pillars"][0],
    "{{SOLUTION_PILLAR_2}}": brief["solution"]["pillars"][1],
    "{{SOLUTION_PILLAR_3}}": brief["solution"]["pillars"][2],
    "{{SOLUTION_FOOTER}}": brief["solution"]["footer"],
    "{{PILOT_TITLE}}": brief["pilot_plan"]["title"],
    "{{PILOT_WINDOW_1}}": brief["pilot_plan"]["phases"][0]["window"],
    "{{PILOT_HEADING_1}}": brief["pilot_plan"]["phases"][0]["heading"],
    "{{PILOT_DETAIL_1}}": brief["pilot_plan"]["phases"][0]["detail"],
    "{{PILOT_WINDOW_2}}": brief["pilot_plan"]["phases"][1]["window"],
    "{{PILOT_HEADING_2}}": brief["pilot_plan"]["phases"][1]["heading"],
    "{{PILOT_DETAIL_2}}": brief["pilot_plan"]["phases"][1]["detail"],
    "{{PILOT_WINDOW_3}}": brief["pilot_plan"]["phases"][2]["window"],
    "{{PILOT_HEADING_3}}": brief["pilot_plan"]["phases"][2]["heading"],
    "{{PILOT_DETAIL_3}}": brief["pilot_plan"]["phases"][2]["detail"],
    "{{PROOF_TITLE}}": brief["proof_points"]["title"],
    "{{PROOF_QUOTE}}": brief["proof_points"]["quote"],
    "{{PROOF_ATTRIBUTION}}": brief["proof_points"]["attribution"],
    "{{PROOF_VALUE_1}}": brief["proof_points"]["stats"][0]["value"],
    "{{PROOF_LABEL_1}}": brief["proof_points"]["stats"][0]["label"],
    "{{PROOF_VALUE_2}}": brief["proof_points"]["stats"][1]["value"],
    "{{PROOF_LABEL_2}}": brief["proof_points"]["stats"][1]["label"],
    "[replace with proof image]": "",
    "{{NEXT_TITLE}}": brief["next_steps"]["title"],
    "{{NEXT_STEP_1}}": brief["next_steps"]["steps"][0],
    "{{NEXT_STEP_2}}": brief["next_steps"]["steps"][1],
    "{{NEXT_STEP_3}}": brief["next_steps"]["steps"][2],
    "{{NEXT_FOOTER}}": brief["next_steps"]["footer"],
}

replace_tokens(prs, token_map)

replace_picture(prs.slides[0], "slot-cover-image", ASSETS_DIR / brief["cover"]["image"])
replace_picture(prs.slides[1], "slot-opportunity-image", ASSETS_DIR / brief["opportunity"]["image"])
replace_picture(prs.slides[4], "slot-proof-image", ASSETS_DIR / brief["proof_points"]["image"])

prs.save(OUTPUT_PATH)
PY
