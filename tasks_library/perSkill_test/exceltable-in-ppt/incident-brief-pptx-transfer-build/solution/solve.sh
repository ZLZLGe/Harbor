#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

INPUT_BRIEF = Path("/root/incident-brief.json")
BRAND_GUIDE = Path("/root/brand-guide.md")
OUTPUT_FILE = Path("/root/results-incident-brief.pptx")

WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def hex_to_rgb(value):
    value = value.strip().lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def parse_brand_guide(path):
    data = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("- ") or ": " not in line:
                continue
            key, value = line[2:].split(": ", 1)
            data[key.strip()] = value.strip()
    return data


def set_background(slide):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG


def add_title(slide, text, left=0.7, top=0.45, width=11.0, height=0.6, size=24):
    shape = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    p = shape.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = PRIMARY
    return shape


with INPUT_BRIEF.open("r", encoding="utf-8") as handle:
    brief = json.load(handle)
brand = parse_brand_guide(BRAND_GUIDE)

PRIMARY = hex_to_rgb(brand["Primary title color"])
ACCENT = hex_to_rgb(brand["Accent badge color"])
BODY = hex_to_rgb(brand["Body text color"])
BG = hex_to_rgb(brand["Background color"])

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Slide 1: cover
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_background(slide)

title_box = slide.shapes.add_textbox(Inches(0.75), Inches(0.8), Inches(8.7), Inches(1.2))
title_p = title_box.text_frame.paragraphs[0]
title_run = title_p.add_run()
title_run.text = brief["report_title"]
title_run.font.size = Pt(28)
title_run.font.bold = True
title_run.font.color.rgb = PRIMARY

subtitle_box = slide.shapes.add_textbox(Inches(0.78), Inches(2.1), Inches(7.8), Inches(0.4))
subtitle_p = subtitle_box.text_frame.paragraphs[0]
subtitle_run = subtitle_p.add_run()
subtitle_run.text = f'{brief["severity"]} | {brief["location"]} | {brief["report_date"]}'
subtitle_run.font.size = Pt(15)
subtitle_run.font.color.rgb = BODY

summary_box = slide.shapes.add_textbox(Inches(0.78), Inches(2.75), Inches(8.4), Inches(2.2))
summary_tf = summary_box.text_frame
summary_tf.word_wrap = True
summary_p = summary_tf.paragraphs[0]
summary_run = summary_p.add_run()
summary_run.text = brief["executive_summary"]
summary_run.font.size = Pt(18)
summary_run.font.color.rgb = BODY

badge = slide.shapes.add_shape(
    MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
    Inches(9.65),
    Inches(0.95),
    Inches(2.0),
    Inches(0.7),
)
badge.fill.solid()
badge.fill.fore_color.rgb = ACCENT
badge.line.color.rgb = ACCENT
badge_tf = badge.text_frame
badge_tf.clear()
badge_p = badge_tf.paragraphs[0]
badge_p.alignment = PP_ALIGN.CENTER
badge_run = badge_p.add_run()
badge_run.text = brief["severity"]
badge_run.font.size = Pt(20)
badge_run.font.bold = True
badge_run.font.color.rgb = WHITE

footer_box = slide.shapes.add_textbox(Inches(0.78), Inches(6.65), Inches(3.5), Inches(0.3))
footer_p = footer_box.text_frame.paragraphs[0]
footer_run = footer_p.add_run()
footer_run.text = brand["Audience line"]
footer_run.font.size = Pt(11)
footer_run.font.color.rgb = BODY

# Slide 2: timeline
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_background(slide)
add_title(slide, "Response timeline")

bar = slide.shapes.add_shape(
    MSO_AUTO_SHAPE_TYPE.RECTANGLE,
    Inches(1.0),
    Inches(1.55),
    Inches(0.08),
    Inches(4.95),
)
bar.fill.solid()
bar.fill.fore_color.rgb = ACCENT
bar.line.color.rgb = ACCENT

top = 1.35
for item in brief["timeline"]:
    dot = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.OVAL,
        Inches(0.88),
        Inches(top + 0.08),
        Inches(0.28),
        Inches(0.28),
    )
    dot.fill.solid()
    dot.fill.fore_color.rgb = ACCENT
    dot.line.color.rgb = ACCENT

    box = slide.shapes.add_textbox(Inches(1.35), Inches(top), Inches(10.8), Inches(0.75))
    p = box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = f'{item["time"]} - {item["event"]}'
    run.font.size = Pt(17)
    run.font.color.rgb = BODY
    top += 0.95

# Slide 3: action table
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_background(slide)
add_title(slide, "48-hour action tracker")

rows = len(brief["actions"]) + 1
cols = 4
table = slide.shapes.add_table(rows, cols, Inches(0.7), Inches(1.4), Inches(11.9), Inches(4.8)).table
headers = ["Owner", "Action", "Due", "Status"]
widths = [1.6, 5.8, 2.1, 1.8]

for idx, width in enumerate(widths):
    table.columns[idx].width = Inches(width)

for idx, header in enumerate(headers):
    cell = table.cell(0, idx)
    cell.text = header
    cell.fill.solid()
    cell.fill.fore_color.rgb = PRIMARY
    p = cell.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.runs[0]
    run.font.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = WHITE

for row_idx, action in enumerate(brief["actions"], start=1):
    values = [action["owner"], action["action"], action["due"], action["status"]]
    for col_idx, value in enumerate(values):
        cell = table.cell(row_idx, col_idx)
        cell.text = value
        cell.fill.solid()
        cell.fill.fore_color.rgb = WHITE
        p = cell.text_frame.paragraphs[0]
        if col_idx == 1:
            p.alignment = PP_ALIGN.LEFT
        else:
            p.alignment = PP_ALIGN.CENTER
        run = p.runs[0]
        run.font.size = Pt(12)
        run.font.color.rgb = BODY

prs.save(str(OUTPUT_FILE))
PY
