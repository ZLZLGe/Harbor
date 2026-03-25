#!/bin/bash
set -euo pipefail

python3 <<'PY'
from __future__ import annotations

import json
import re
from pathlib import Path

from cairosvg import svg2png
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

BRIEF_PATH = Path("/root/brief.md")
METRICS_PATH = Path("/root/metrics.json")
PALETTE_PATH = Path("/root/brand/palette.json")
WORDMARK_SVG = Path("/root/brand/support-wordmark.svg")
WORDMARK_PNG = Path("/tmp/support-wordmark.png")
OUTPUT_PATH = Path("/root/Support-Onboarding-playbook.pptx")


def rgb(hex_value: str) -> RGBColor:
    value = hex_value.strip().lstrip("#")
    return RGBColor.from_string(value)


def parse_brief(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")

    def section(name: str) -> str:
        pattern = rf"## {re.escape(name)}\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, text, re.S)
        if not match:
            raise ValueError(f"missing section: {name}")
        return match.group(1).strip()

    cover = section("Cover")
    workflow = section("Workflow")
    closing = section("Closing")

    cover_title = re.search(r"Title:\s*(.+)", cover).group(1).strip()
    cover_subtitle = re.search(r"Subtitle:\s*(.+)", cover).group(1).strip()
    cover_tagline = re.search(r"Tagline:\s*(.+)", cover).group(1).strip()

    agenda = [match.strip() for match in re.findall(r"^\d+\.\s+(.+)$", section("Agenda"), re.M)]

    workflow_title = re.search(r"Title:\s*(.+)", workflow).group(1).strip()
    workflow_intro = re.search(r"Intro:\s*(.+)", workflow).group(1).strip()
    workflow_steps = []
    for line in workflow.splitlines():
        if not line.startswith("- "):
            continue
        stage, description, owner = [part.strip() for part in line[2:].split("|")]
        workflow_steps.append({"stage": stage, "description": description, "owner": owner})

    closing_title = re.search(r"Title:\s*(.+)", closing).group(1).strip()
    closing_bullets = [match.strip() for match in re.findall(r"^- (.+)$", closing, re.M)]
    closing_footer = re.search(r"Footer:\s*(.+)", closing).group(1).strip()

    return {
        "cover_title": cover_title,
        "cover_subtitle": cover_subtitle,
        "cover_tagline": cover_tagline,
        "agenda": agenda,
        "workflow_title": workflow_title,
        "workflow_intro": workflow_intro,
        "workflow_steps": workflow_steps,
        "closing_title": closing_title,
        "closing_bullets": closing_bullets,
        "closing_footer": closing_footer,
    }


def set_run_style(run, *, font_name: str, size: int, color: str, bold: bool = False, italic: bool = False) -> None:
    run.font.name = font_name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = rgb(color)


def add_full_background(slide, color: str) -> None:
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        0,
        0,
        prs.slide_width,
        prs.slide_height,
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)
    shape.line.fill.background()


def add_title_band(slide, title: str, palette: dict[str, str]) -> None:
    band = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        0,
        0,
        prs.slide_width,
        Inches(0.95),
    )
    band.fill.solid()
    band.fill.fore_color.rgb = rgb(palette["primary"])
    band.line.fill.background()

    accent = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0.45),
        Inches(0.95),
        Inches(1.0),
        Inches(0.12),
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = rgb(palette["accent"])
    accent.line.fill.background()

    box = slide.shapes.add_textbox(Inches(0.6), Inches(0.18), Inches(8.5), Inches(0.5))
    frame = box.text_frame
    frame.clear()
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.LEFT
    run = paragraph.add_run()
    run.text = title
    set_run_style(run, font_name=palette["font"], size=24, color="FFFFFF", bold=True)


def add_wordmark(slide, left: float, top: float, width: float) -> None:
    slide.shapes.add_picture(str(WORDMARK_PNG), Inches(left), Inches(top), width=Inches(width))


def add_cover(slide, brief: dict[str, object], palette: dict[str, str]) -> None:
    add_full_background(slide, palette["canvas"])

    panel = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(0.55),
        Inches(0.55),
        Inches(12.2),
        Inches(6.35),
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = rgb("FFFFFF")
    panel.line.color.rgb = rgb(palette["primary"])
    panel.line.width = Pt(1.5)

    hero = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0.55),
        Inches(0.55),
        Inches(3.4),
        Inches(6.35),
    )
    hero.fill.solid()
    hero.fill.fore_color.rgb = rgb(palette["primary"])
    hero.line.fill.background()

    badge = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(4.35),
        Inches(1.15),
        Inches(2.0),
        Inches(0.48),
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = rgb(palette["accent"])
    badge.line.fill.background()
    badge_text = badge.text_frame
    badge_text.clear()
    p = badge_text.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "Transfer deck"
    set_run_style(r, font_name=palette["font"], size=14, color="FFFFFF", bold=True)

    add_wordmark(slide, 4.25, 5.55, 4.2)

    title_box = slide.shapes.add_textbox(Inches(4.35), Inches(1.9), Inches(7.5), Inches(1.3))
    tf = title_box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = brief["cover_title"]
    set_run_style(r, font_name=palette["font"], size=28, color=palette["primary"], bold=True)

    subtitle_box = slide.shapes.add_textbox(Inches(4.35), Inches(3.25), Inches(7.1), Inches(0.9))
    tf = subtitle_box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = brief["cover_subtitle"]
    set_run_style(r, font_name=palette["font"], size=18, color=palette["text"])

    tagline_box = slide.shapes.add_textbox(Inches(4.35), Inches(4.25), Inches(7.1), Inches(0.9))
    tf = tagline_box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = brief["cover_tagline"]
    set_run_style(r, font_name=palette["font"], size=16, color=palette["muted"], italic=True)

    left_caption = slide.shapes.add_textbox(Inches(0.95), Inches(1.5), Inches(2.2), Inches(3.2))
    tf = left_caption.text_frame
    tf.clear()
    for index, line in enumerate(["New-hire", "queue rhythm", "handoff", "standards"]):
        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.alignment = PP_ALIGN.LEFT
        run = paragraph.add_run()
        run.text = line
        set_run_style(run, font_name=palette["font"], size=24 if index == 0 else 20, color="FFFFFF", bold=True)


def add_agenda(slide, brief: dict[str, object], palette: dict[str, str]) -> None:
    add_full_background(slide, palette["canvas"])
    add_title_band(slide, "Agenda", palette)

    for idx, item in enumerate(brief["agenda"], start=1):
        top = 1.45 + (idx - 1) * 1.2
        badge = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(0.9),
            Inches(top),
            Inches(0.52),
            Inches(0.52),
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = rgb(palette["accent"])
        badge.line.fill.background()
        tf = badge.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = str(idx)
        set_run_style(run, font_name=palette["font"], size=15, color="FFFFFF", bold=True)

        box = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(1.65),
            Inches(top - 0.06),
            Inches(10.7),
            Inches(0.72),
        )
        box.fill.solid()
        box.fill.fore_color.rgb = rgb("FFFFFF")
        box.line.color.rgb = rgb(palette["primary"])
        box.line.width = Pt(1.0)
        text_frame = box.text_frame
        text_frame.clear()
        p = text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = item
        set_run_style(run, font_name=palette["font"], size=18, color=palette["text"])


def add_workflow(slide, brief: dict[str, object], palette: dict[str, str]) -> None:
    add_full_background(slide, palette["canvas"])
    add_title_band(slide, brief["workflow_title"], palette)

    intro_box = slide.shapes.add_textbox(Inches(0.65), Inches(1.2), Inches(11.5), Inches(0.5))
    intro_frame = intro_box.text_frame
    intro_frame.clear()
    p = intro_frame.paragraphs[0]
    r = p.add_run()
    r.text = brief["workflow_intro"]
    set_run_style(r, font_name=palette["font"], size=14, color=palette["muted"])

    lefts = [0.55, 3.4, 6.25, 9.1]
    for idx, (left, step) in enumerate(zip(lefts, brief["workflow_steps"]), start=1):
        card = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(left),
            Inches(1.95),
            Inches(2.45),
            Inches(3.75),
        )
        card.fill.solid()
        card.fill.fore_color.rgb = rgb("FFFFFF")
        card.line.color.rgb = rgb(palette["primary"])
        card.line.width = Pt(1.2)

        number = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(left + 0.18),
            Inches(2.15),
            Inches(0.5),
            Inches(0.5),
        )
        number.fill.solid()
        number.fill.fore_color.rgb = rgb(palette["accent"])
        number.line.fill.background()
        tf = number.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(idx)
        set_run_style(r, font_name=palette["font"], size=14, color="FFFFFF", bold=True)

        stage_box = slide.shapes.add_textbox(Inches(left + 0.2), Inches(2.8), Inches(2.0), Inches(0.6))
        tf = stage_box.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = step["stage"]
        set_run_style(r, font_name=palette["font"], size=18, color=palette["primary"], bold=True)

        desc_box = slide.shapes.add_textbox(Inches(left + 0.2), Inches(3.45), Inches(2.0), Inches(1.35))
        tf = desc_box.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = step["description"]
        set_run_style(r, font_name=palette["font"], size=12, color=palette["text"])

        owner_box = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(left + 0.2),
            Inches(5.0),
            Inches(2.0),
            Inches(0.48),
        )
        owner_box.fill.solid()
        owner_box.fill.fore_color.rgb = rgb("F0F7FA")
        owner_box.line.fill.background()
        owner_tf = owner_box.text_frame
        owner_tf.clear()
        p = owner_tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = step["owner"]
        set_run_style(r, font_name=palette["font"], size=11, color=palette["primary"], bold=True)


def add_metrics(slide, metrics: dict[str, object], palette: dict[str, str]) -> None:
    add_full_background(slide, palette["canvas"])
    add_title_band(slide, metrics["slide_title"], palette)

    kpi = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(0.75),
        Inches(1.4),
        Inches(3.0),
        Inches(2.0),
    )
    kpi.fill.solid()
    kpi.fill.fore_color.rgb = rgb(palette["accent"])
    kpi.line.fill.background()
    frame = kpi.text_frame
    frame.clear()
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = metrics["headline_metric"]["value"]
    set_run_style(r, font_name=palette["font"], size=28, color="FFFFFF", bold=True)
    p = frame.add_paragraph()
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = metrics["headline_metric"]["label"]
    set_run_style(r, font_name=palette["font"], size=15, color="FFFFFF", bold=True)
    p = frame.add_paragraph()
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = metrics["headline_metric"]["note"]
    set_run_style(r, font_name=palette["font"], size=11, color="FFFFFF")

    rows = 1 + len(metrics["table"]["rows"])
    cols = len(metrics["table"]["columns"])
    table_shape = slide.shapes.add_table(rows, cols, Inches(4.15), Inches(1.48), Inches(8.15), Inches(3.8))
    table = table_shape.table

    for col_idx, value in enumerate(metrics["table"]["columns"]):
        cell = table.cell(0, col_idx)
        cell.text = value
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(palette["primary"])
        paragraph = cell.text_frame.paragraphs[0]
        paragraph.alignment = PP_ALIGN.CENTER
        run = paragraph.runs[0]
        set_run_style(run, font_name=palette["font"], size=13, color="FFFFFF", bold=True)

    for row_idx, row in enumerate(metrics["table"]["rows"], start=1):
        for col_idx, value in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.text = value
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb("FFFFFF" if row_idx % 2 else "F0F7FA")
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.alignment = PP_ALIGN.LEFT if col_idx == 0 else PP_ALIGN.CENTER
            run = paragraph.runs[0]
            set_run_style(run, font_name=palette["font"], size=12, color=palette["text"])


def add_closing(slide, brief: dict[str, object], palette: dict[str, str]) -> None:
    add_full_background(slide, palette["canvas"])
    add_title_band(slide, brief["closing_title"], palette)

    bullet_box = slide.shapes.add_textbox(Inches(0.85), Inches(1.55), Inches(6.6), Inches(3.0))
    tf = bullet_box.text_frame
    tf.clear()
    for idx, bullet in enumerate(brief["closing_bullets"]):
        paragraph = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        paragraph.text = bullet
        paragraph.level = 0
        paragraph.space_after = Pt(10)
        paragraph.alignment = PP_ALIGN.LEFT
        run = paragraph.runs[0]
        set_run_style(run, font_name=palette["font"], size=18, color=palette["text"])

    footer_box = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(0.85),
        Inches(5.05),
        Inches(7.2),
        Inches(0.8),
    )
    footer_box.fill.solid()
    footer_box.fill.fore_color.rgb = rgb(palette["accent"])
    footer_box.line.fill.background()
    footer_tf = footer_box.text_frame
    footer_tf.clear()
    footer_tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = footer_tf.paragraphs[0]
    paragraph.alignment = PP_ALIGN.CENTER
    run = paragraph.add_run()
    run.text = brief["closing_footer"]
    set_run_style(run, font_name=palette["font"], size=15, color="FFFFFF", bold=True)

    add_wordmark(slide, 8.3, 2.0, 3.5)


brief = parse_brief(BRIEF_PATH)
metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
palette = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))
svg2png(url=str(WORDMARK_SVG), write_to=str(WORDMARK_PNG), output_width=1200)

prs = Presentation()
prs.slide_width = Inches(13.333333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]

cover = prs.slides.add_slide(blank)
add_cover(cover, brief, palette)

agenda = prs.slides.add_slide(blank)
add_agenda(agenda, brief, palette)

workflow = prs.slides.add_slide(blank)
add_workflow(workflow, brief, palette)

metrics_slide = prs.slides.add_slide(blank)
add_metrics(metrics_slide, metrics, palette)

closing = prs.slides.add_slide(blank)
add_closing(closing, brief, palette)

prs.save(str(OUTPUT_PATH))
PY
