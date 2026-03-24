#!/bin/bash
set -euo pipefail

SKILL_DIR=/root/.codex/skills/pptx
WORK_DIR=/tmp/onboarding-template-remix

mkdir -p "$WORK_DIR"

python3 "$SKILL_DIR/scripts/rearrange.py" \
  /root/Northstar-Brand-Template.pptx \
  "$WORK_DIR/working.pptx" \
  0,6,2,3,4,5

python3 "$SKILL_DIR/scripts/inventory.py" \
  "$WORK_DIR/working.pptx" \
  "$WORK_DIR/inventory.json"

python3 <<'PY'
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

inventory = json.loads(Path("/tmp/onboarding-template-remix/inventory.json").read_text())


def find_shape(slide_key: str, marker: str) -> tuple[str, dict]:
    for shape_key, shape in inventory[slide_key].items():
        paragraphs = shape.get("paragraphs", [])
        texts = [p.get("text", "").strip() for p in paragraphs if p.get("text", "").strip()]
        if not texts:
            continue
        if texts[0] == marker or marker in texts:
            return shape_key, shape
    raise KeyError(f"Could not find marker {marker!r} on {slide_key}")


def paragraph_template(shape: dict) -> dict:
    paragraphs = shape.get("paragraphs", [])
    if paragraphs:
        template = deepcopy(paragraphs[0])
        template.pop("text", None)
        return template
    return {}


def make_paragraph(shape: dict, text: str, *, bullet: bool = False, level: int = 0, **overrides) -> dict:
    paragraph = paragraph_template(shape)
    paragraph.pop("bullet", None)
    paragraph.pop("level", None)
    paragraph["text"] = text
    if bullet:
        paragraph["bullet"] = True
        paragraph["level"] = level
        if "alignment" not in overrides:
            paragraph.pop("alignment", None)
    for key, value in overrides.items():
        paragraph[key] = value
    return paragraph


slide0_key, slide0_shape = find_shape("slide-0", "Northstar Labs")
slide1_title_key, slide1_title_shape = find_shape("slide-1", "[Insert checklist or support topic]")
slide1_body_key, slide1_body_shape = find_shape(
    "slide-1",
    "[Use this layout for practical guidance, a role list, or step-by-step expectations for new hires.]",
)
slide1_banner_key, slide1_banner_shape = find_shape("slide-1", "[Add a short why-this-matters line here]")
slide2_title_key, slide2_title_shape = find_shape("slide-2", "[Insert workflow or culture topic]")
slide2_body_key, slide2_body_shape = find_shape(
    "slide-2",
    "[Use this layout for a deeper narrative block that explains how the team works day to day.]",
)
slide2_banner_key, slide2_banner_shape = find_shape("slide-2", "[Add a bottom banner message here]")
slide3_title_key, slide3_title_shape = find_shape("slide-3", "[Insert divider headline]")
slide3_body_key, slide3_body_shape = find_shape("slide-3", "[Optional short divider caption]")
slide4_title_key, slide4_title_shape = find_shape("slide-4", "[Insert checklist or support topic]")
slide4_body_key, slide4_body_shape = find_shape(
    "slide-4",
    "[Use this layout for practical guidance, a role list, or step-by-step expectations for new hires.]",
)
slide4_banner_key, slide4_banner_shape = find_shape("slide-4", "[Add a short why-this-matters line here]")
slide5_title_key, slide5_title_shape = find_shape("slide-5", "[Insert resources or contacts topic]")
slide5_body_key, slide5_body_shape = find_shape(
    "slide-5",
    "[Use this layout for tools, channels, escalation paths, or first-month reminders.]",
)
slide5_banner_key, slide5_banner_shape = find_shape("slide-5", "[Add a next-step banner here]")

cover_font_size = paragraph_template(slide0_shape).get("font_size", 30.0)
subtitle_font_size = max(18.0, round(cover_font_size * 0.55, 1))

replacements = {
    "slide-0": {
        slide0_key: {
            "paragraphs": [
                make_paragraph(slide0_shape, "Welcome to Harbor Product Engineering", alignment="CENTER", bold=True),
                make_paragraph(
                    slide0_shape,
                    "Spring 2026 new hire guide",
                    alignment="CENTER",
                    bold=False,
                    font_size=subtitle_font_size,
                ),
            ]
        }
    },
    "slide-1": {
        slide1_title_key: {"paragraphs": [make_paragraph(slide1_title_shape, "Your First Week Roadmap", bold=True)]},
        slide1_body_key: {
            "paragraphs": [
                make_paragraph(slide1_body_shape, "Day 1: Set up accounts, devices, and local dev tools.", bullet=True),
                make_paragraph(
                    slide1_body_shape,
                    "Day 2: Tour the roadmap, the customer journey, and active squads.",
                    bullet=True,
                ),
                make_paragraph(
                    slide1_body_shape,
                    "Day 3: Shadow standup, planning, and design review.",
                    bullet=True,
                ),
                make_paragraph(
                    slide1_body_shape,
                    "Day 4: Pair on a low-risk fix and ship your first change.",
                    bullet=True,
                ),
                make_paragraph(
                    slide1_body_shape,
                    "Day 5: Capture questions, meet your manager, and plan week two.",
                    bullet=True,
                ),
            ]
        },
        slide1_banner_key: {
            "paragraphs": [
                make_paragraph(
                    slide1_banner_shape,
                    "Ship early, ask often, document what you learn.",
                )
            ]
        },
    },
    "slide-2": {
        slide2_title_key: {"paragraphs": [make_paragraph(slide2_title_shape, "How We Build and Ship", bold=True)]},
        slide2_body_key: {
            "paragraphs": [
                make_paragraph(
                    slide2_body_shape,
                    "Product engineering runs in cross-functional squads with a weekly planning rhythm, lightweight RFCs for meaningful changes, and demos at the end of every sprint. You are expected to share progress in the open, surface blockers early, and leave a clear trail in tickets and docs.",
                )
            ]
        },
        slide2_banner_key: {
            "paragraphs": [
                make_paragraph(slide2_banner_shape, "Small PRs, visible decisions, steady releases.")
            ]
        },
    },
    "slide-3": {
        slide3_title_key: {"paragraphs": [make_paragraph(slide3_title_shape, "Operating Norms", bold=True)]},
        slide3_body_key: {
            "paragraphs": [
                make_paragraph(
                    slide3_body_shape,
                    "Default to clarity, keep handoffs small, and close every loop with the next owner.",
                )
            ]
        },
    },
    "slide-4": {
        slide4_title_key: {"paragraphs": [make_paragraph(slide4_title_shape, "Your Support Network", bold=True)]},
        slide4_body_key: {
            "paragraphs": [
                make_paragraph(
                    slide4_body_shape,
                    "Manager: prioritization, feedback, and 30-day goals.",
                    bullet=True,
                ),
                make_paragraph(
                    slide4_body_shape,
                    "Onboarding buddy: team rituals, codebase navigation, and local setup questions.",
                    bullet=True,
                ),
                make_paragraph(
                    slide4_body_shape,
                    "IT help desk: hardware, SSO, VPN, and access recovery.",
                    bullet=True,
                ),
                make_paragraph(
                    slide4_body_shape,
                    "People Ops: benefits, travel policy, and onboarding logistics.",
                    bullet=True,
                ),
            ]
        },
        slide4_banner_key: {
            "paragraphs": [
                make_paragraph(
                    slide4_banner_shape,
                    "You should never be blocked alone for more than one working session.",
                )
            ]
        },
    },
    "slide-5": {
        slide5_title_key: {"paragraphs": [make_paragraph(slide5_title_shape, "First 30 Days", bold=True)]},
        slide5_body_key: {
            "paragraphs": [
                make_paragraph(
                    slide5_body_shape,
                    "Complete environment setup and core product walkthroughs.",
                    bullet=True,
                ),
                make_paragraph(
                    slide5_body_shape,
                    "Review one customer problem area with your squad.",
                    bullet=True,
                ),
                make_paragraph(
                    slide5_body_shape,
                    "Own one scoped change from planning through release.",
                    bullet=True,
                ),
                make_paragraph(
                    slide5_body_shape,
                    "Write a short onboarding reflection with follow-up questions.",
                    bullet=True,
                ),
            ]
        },
        slide5_banner_key: {
            "paragraphs": [
                make_paragraph(
                    slide5_banner_shape,
                    "Aim for context, confidence, and one shipped improvement.",
                )
            ]
        },
    },
}

Path("/tmp/onboarding-template-remix/replacements.json").write_text(json.dumps(replacements, indent=2))
PY

python3 "$SKILL_DIR/scripts/replace.py" \
  "$WORK_DIR/working.pptx" \
  "$WORK_DIR/replacements.json" \
  /root/Team-Onboarding-Branded.pptx
