from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

INPUT_PPTX = Path("/root/Northstar-Brand-Template.pptx")
OUTPUT_PPTX = Path("/root/Team-Onboarding-Branded.pptx")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

EXPECTED_SLIDES = [
    [
        "Welcome to Harbor Product Engineering",
        "Spring 2026 new hire guide",
    ],
    [
        "Your First Week Roadmap",
        "Day 1: Set up accounts, devices, and local dev tools.",
        "Day 2: Tour the roadmap, the customer journey, and active squads.",
        "Day 3: Shadow standup, planning, and design review.",
        "Day 4: Pair on a low-risk fix and ship your first change.",
        "Day 5: Capture questions, meet your manager, and plan week two.",
        "Ship early, ask often, document what you learn.",
    ],
    [
        "How We Build and Ship",
        "Product engineering runs in cross-functional squads with a weekly planning rhythm, lightweight RFCs for meaningful changes, and demos at the end of every sprint. You are expected to share progress in the open, surface blockers early, and leave a clear trail in tickets and docs.",
        "Small PRs, visible decisions, steady releases.",
    ],
    [
        "Operating Norms",
        "Default to clarity, keep handoffs small, and close every loop with the next owner.",
    ],
    [
        "Your Support Network",
        "Manager: prioritization, feedback, and 30-day goals.",
        "Onboarding buddy: team rituals, codebase navigation, and local setup questions.",
        "IT help desk: hardware, SSO, VPN, and access recovery.",
        "People Ops: benefits, travel policy, and onboarding logistics.",
        "You should never be blocked alone for more than one working session.",
    ],
    [
        "First 30 Days",
        "Complete environment setup and core product walkthroughs.",
        "Review one customer problem area with your squad.",
        "Own one scoped change from planning through release.",
        "Write a short onboarding reflection with follow-up questions.",
        "Aim for context, confidence, and one shipped improvement.",
    ],
]

EXPECTED_TEMPLATE_SEQUENCE = [0, 6, 2, 3, 4, 5]


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        (
            name
            for name in zipf.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ),
        key=slide_number,
    )


def slide_root(zipf: zipfile.ZipFile, slide_name: str) -> ET.Element:
    return ET.fromstring(zipf.read(slide_name))


def slide_paragraphs(slide: ET.Element) -> list[ET.Element]:
    paragraphs = []
    for paragraph in slide.findall(".//a:p", NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//a:t", NS))
        text = " ".join(text.split())
        if text:
            paragraphs.append(paragraph)
    return paragraphs


def paragraph_text(paragraph: ET.Element) -> str:
    return " ".join("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).split())


def paragraph_is_bulleted(paragraph: ET.Element) -> bool:
    ppr = paragraph.find("a:pPr", NS)
    if ppr is None:
        return False
    return ppr.find("a:buChar", NS) is not None or ppr.find("a:buAutoNum", NS) is not None


def slide_structure_signature(slide: ET.Element) -> str:
    normalized = ET.fromstring(ET.tostring(slide, encoding="utf-8"))
    for tx_body in normalized.findall(".//p:txBody", NS):
        for child in list(tx_body):
            if child.tag in {
                f"{{{NS['a']}}}bodyPr",
                f"{{{NS['a']}}}lstStyle",
            }:
                continue
            tx_body.remove(child)
    return hashlib.sha256(ET.tostring(normalized, encoding="utf-8")).hexdigest()


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "Expected onboarding presentation to be created"
    assert OUTPUT_PPTX.stat().st_size > 0, "Output presentation is empty"


def test_slide_count_and_text() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        assert len(slide_names) == 6, "Expected exactly six slides"
        actual = []
        for slide_name in slide_names:
            actual.append([paragraph_text(p) for p in slide_paragraphs(slide_root(zipf, slide_name))])
    assert actual == EXPECTED_SLIDES


def test_bullet_slides_use_real_bullets() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        slide2 = slide_paragraphs(slide_root(zipf, slide_names[1]))
        slide5 = slide_paragraphs(slide_root(zipf, slide_names[4]))
        slide6 = slide_paragraphs(slide_root(zipf, slide_names[5]))

    for paragraph in slide2[1:6]:
        assert paragraph_is_bulleted(paragraph), "Week-one roadmap items must use bullet formatting"
    for paragraph in slide5[1:5]:
        assert paragraph_is_bulleted(paragraph), "Support-network items must use bullet formatting"
    for paragraph in slide6[1:5]:
        assert paragraph_is_bulleted(paragraph), "First-30-days items must use bullet formatting"


def test_output_reuses_and_reorders_template_slides() -> None:
    with zipfile.ZipFile(INPUT_PPTX, "r") as input_zip, zipfile.ZipFile(OUTPUT_PPTX, "r") as output_zip:
        template_slide_names = iter_slide_names(input_zip)
        output_slide_names = iter_slide_names(output_zip)
        actual_sequence = [
            slide_structure_signature(slide_root(output_zip, slide_name))
            for slide_name in output_slide_names
        ]
        expected_sequence = [
            slide_structure_signature(slide_root(input_zip, template_slide_names[index]))
            for index in EXPECTED_TEMPLATE_SEQUENCE
        ]

    assert (
        actual_sequence == expected_sequence
    ), "Expected the final deck to reuse and reorder the template slides instead of rebuilding them from scratch"


def test_placeholders_are_cleared() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        texts = []
        for slide_name in iter_slide_names(zipf):
            texts.extend(paragraph_text(p) for p in slide_paragraphs(slide_root(zipf, slide_name)))
    for text in texts:
        assert "[" not in text and "]" not in text, f"Placeholder text leaked into output: {text}"


def test_template_theme_and_brand_asset_are_preserved() -> None:
    with zipfile.ZipFile(INPUT_PPTX, "r") as input_zip, zipfile.ZipFile(OUTPUT_PPTX, "r") as output_zip:
        assert input_zip.read("ppt/theme/theme1.xml") == output_zip.read(
            "ppt/theme/theme1.xml"
        ), "Theme file changed; expected the template theme to be preserved"
        assert input_zip.read("ppt/media/image1.png") == output_zip.read(
            "ppt/media/image1.png"
        ), "Expected branded media asset to be preserved from the template"
