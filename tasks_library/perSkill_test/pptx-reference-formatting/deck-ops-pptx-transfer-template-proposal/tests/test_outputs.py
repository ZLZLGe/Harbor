from __future__ import annotations

import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

TEMPLATE_PPTX = Path("/root/GreenGrid-Template-Workbook.pptx")
BRIEF_PATH = Path("/root/proposal_brief.yaml")
ASSETS_DIR = Path("/root/proposal-assets")
OUTPUT_PPTX = Path("/root/GreenGrid-Proposal-tailored.pptx")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def load_brief() -> dict:
    return yaml.safe_load(BRIEF_PATH.read_text(encoding="utf-8"))


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else -1

    return sorted(
        (name for name in zipf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
        key=slide_number,
    )


def slide_root(zipf: zipfile.ZipFile, slide_index: int) -> ET.Element:
    return ET.fromstring(zipf.read(iter_slide_names(zipf)[slide_index - 1]))


def paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.findall(".//a:t", NS))


def normalize(text: str) -> str:
    return " ".join(text.split())


def slide_texts(slide: ET.Element) -> list[str]:
    texts: list[str] = []
    for paragraph in slide.findall(".//a:p", NS):
        text = normalize(paragraph_text(paragraph))
        if text:
            texts.append(text)
    return texts


def get_slide_dimensions(zipf: zipfile.ZipFile) -> tuple[int, int]:
    root = ET.fromstring(zipf.read("ppt/presentation.xml"))
    size = root.find(".//p:sldSz", NS)
    assert size is not None, "missing slide size"
    return int(size.get("cx")), int(size.get("cy"))


def theme_signature(zipf: zipfile.ZipFile) -> dict[str, object]:
    root = ET.fromstring(zipf.read("ppt/theme/theme1.xml"))
    colors = {}
    for key in ("accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"):
        node = root.find(f".//a:clrScheme/a:{key}/a:srgbClr", NS)
        colors[key] = node.get("val") if node is not None else None
    major_latin = root.find(".//a:fontScheme/a:majorFont/a:latin", NS)
    minor_latin = root.find(".//a:fontScheme/a:minorFont/a:latin", NS)
    return {
        "colors": colors,
        "major": major_latin.get("typeface") if major_latin is not None else None,
        "minor": minor_latin.get("typeface") if minor_latin is not None else None,
    }


def layout_targets(zipf: zipfile.ZipFile) -> list[str]:
    targets: list[str] = []
    for rel_path in sorted(name for name in zipf.namelist() if re.fullmatch(r"ppt/slides/_rels/slide\d+\.xml\.rels", name)):
        rel_root = ET.fromstring(zipf.read(rel_path))
        for rel in rel_root.findall("rel:Relationship", NS):
            if rel.get("Type", "").endswith("/slideLayout"):
                targets.append(rel.get("Target"))
    return targets


def resolve_target(part_name: str, target: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(part_name), target))


def slide_image_payloads(zipf: zipfile.ZipFile, slide_index: int) -> list[bytes]:
    slide_name = iter_slide_names(zipf)[slide_index - 1]
    rel_name = posixpath.join(
        posixpath.dirname(slide_name),
        "_rels",
        posixpath.basename(slide_name) + ".rels",
    )
    rel_root = ET.fromstring(zipf.read(rel_name))
    payloads: list[bytes] = []
    for rel in rel_root.findall("rel:Relationship", NS):
        if not rel.get("Type", "").endswith("/image"):
            continue
        target = rel.get("Target")
        assert target is not None
        payloads.append(zipf.read(resolve_target(slide_name, target)))
    return payloads


def visible_text_dump(zipf: zipfile.ZipFile) -> str:
    all_text: list[str] = []
    for index in range(1, len(iter_slide_names(zipf)) + 1):
        all_text.extend(slide_texts(slide_root(zipf, index)))
    return "\n".join(all_text)


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "expected output deck at /root/GreenGrid-Proposal-tailored.pptx"
    assert OUTPUT_PPTX.stat().st_size > 0, "output deck is empty"


def test_output_has_exactly_six_slides() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX) as zipf:
        assert len(iter_slide_names(zipf)) == 6, "expected exactly 6 slides in the tailored proposal"


def test_slide_size_theme_and_layout_family_are_preserved() -> None:
    with zipfile.ZipFile(TEMPLATE_PPTX) as template_zip, zipfile.ZipFile(OUTPUT_PPTX) as output_zip:
        assert get_slide_dimensions(output_zip) == get_slide_dimensions(template_zip), "slide size changed unexpectedly"
        assert theme_signature(output_zip) == theme_signature(template_zip), "template theme was not preserved"
        template_layouts = set(layout_targets(template_zip))
        output_layouts = set(layout_targets(output_zip))
        assert output_layouts <= template_layouts, "slide layouts should come from the template family"


def test_slide_order_matches_required_sections() -> None:
    brief = load_brief()
    expected_titles = [
        brief["cover"]["title"],
        brief["opportunity"]["title"],
        brief["solution"]["title"],
        brief["pilot_plan"]["title"],
        brief["proof_points"]["title"],
        brief["next_steps"]["title"],
    ]

    with zipfile.ZipFile(OUTPUT_PPTX) as zipf:
        for index, expected_title in enumerate(expected_titles, start=1):
            texts = slide_texts(slide_root(zipf, index))
            assert expected_title in texts, f"slide {index} is missing its required section title"


def test_required_copy_is_present_on_each_slide() -> None:
    brief = load_brief()
    with zipfile.ZipFile(OUTPUT_PPTX) as zipf:
        cover_texts = slide_texts(slide_root(zipf, 1))
        assert brief["cover"]["kicker"] in cover_texts, "cover kicker missing"
        assert brief["cover"]["subtitle"] in cover_texts, "cover subtitle missing"
        assert brief["cover"]["tagline"] in cover_texts, "cover tagline missing"

        opportunity_texts = slide_texts(slide_root(zipf, 2))
        assert brief["opportunity"]["intro"] in opportunity_texts, "opportunity intro missing"
        for bullet in brief["opportunity"]["bullets"]:
            assert bullet in opportunity_texts, f"missing opportunity bullet: {bullet}"
        assert brief["opportunity"]["stat_label"] in opportunity_texts, "opportunity stat label missing"
        assert brief["opportunity"]["stat_value"] in opportunity_texts, "opportunity stat value missing"

        solution_texts = slide_texts(slide_root(zipf, 3))
        assert brief["solution"]["intro"] in solution_texts, "solution intro missing"
        for pillar in brief["solution"]["pillars"]:
            assert pillar in solution_texts, f"missing solution pillar: {pillar}"
        assert brief["solution"]["footer"] in solution_texts, "solution footer missing"

        pilot_texts = slide_texts(slide_root(zipf, 4))
        for phase in brief["pilot_plan"]["phases"]:
            assert phase["window"] in pilot_texts, f"missing pilot phase window: {phase['window']}"
            assert phase["heading"] in pilot_texts, f"missing pilot phase heading: {phase['heading']}"
            assert phase["detail"] in pilot_texts, f"missing pilot phase detail: {phase['detail']}"

        proof_texts = slide_texts(slide_root(zipf, 5))
        assert brief["proof_points"]["quote"] in proof_texts, "proof quote missing"
        assert brief["proof_points"]["attribution"] in proof_texts, "proof attribution missing"
        for stat in brief["proof_points"]["stats"]:
            assert stat["value"] in proof_texts, f"missing proof stat value: {stat['value']}"
            assert stat["label"] in proof_texts, f"missing proof stat label: {stat['label']}"

        next_texts = slide_texts(slide_root(zipf, 6))
        for step in brief["next_steps"]["steps"]:
            assert step in next_texts, f"missing next-step bullet: {step}"
        assert brief["next_steps"]["footer"] in next_texts, "next-steps footer missing"


def test_required_images_are_embedded_on_the_expected_slides() -> None:
    brief = load_brief()
    expected = {
        1: (ASSETS_DIR / brief["cover"]["image"]).read_bytes(),
        2: (ASSETS_DIR / brief["opportunity"]["image"]).read_bytes(),
        5: (ASSETS_DIR / brief["proof_points"]["image"]).read_bytes(),
    }

    with zipfile.ZipFile(OUTPUT_PPTX) as zipf:
        for slide_index, expected_bytes in expected.items():
            payloads = slide_image_payloads(zipf, slide_index)
            assert payloads, f"slide {slide_index} should contain an embedded image"
            assert any(payload == expected_bytes for payload in payloads), f"slide {slide_index} is missing the required image asset"


def test_no_visible_placeholders_or_editing_notes_remain() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX) as zipf:
        payload = visible_text_dump(zipf)
        lowered = payload.lower()
        assert "{{" not in payload and "}}" not in payload, "visible token placeholders remained in the output"
        assert "[replace" not in lowered, "image replacement prompt remained visible"
        assert "[delete" not in lowered, "template deletion prompt remained visible"
        assert "template divider" not in lowered, "unused divider slide content remained"
        assert "unused template option" not in lowered, "unused template note remained"
