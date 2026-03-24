from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

INPUT_PPTX = Path("/root/AI-Summit-Sessions.pptx")
OUTPUT_PPTX = Path("/root/AI-Summit-Sessions_processed.pptx")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

TITLE_RE = re.compile(r"^Session\s+(\d{3}):\s+.+$")
GT_TITLES = {
    2: "Session 310: Agentic CFD Pipelines",
    3: "Session 105: Reasoning + Acting Systems",
    4: "Session 105: Reasoning + Acting Systems",
    5: "Session 220: Failure Taxonomy for Multi-Agent Apps",
    6: "Session 405: Benchmarking Collaborative Agents",
}
GT_INDEX = [
    "Session 105: Reasoning + Acting Systems",
    "Session 220: Failure Taxonomy for Multi-Agent Apps",
    "Session 310: Agentic CFD Pipelines",
    "Session 405: Benchmarking Collaborative Agents",
]


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        (name for name in zipf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")),
        key=slide_number,
    )


def load_slide(zipf: zipfile.ZipFile, slide_names: list[str], slide_index: int) -> ET.Element:
    return ET.fromstring(zipf.read(slide_names[slide_index - 1]))


def paragraph_text(paragraph: ET.Element) -> str:
    return " ".join("".join(t.text or "" for t in paragraph.findall(".//a:t", NS)).split())


def build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def find_shape_for_paragraph(paragraph: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = paragraph
    while current in parent_map:
        current = parent_map[current]
        if current.tag.endswith("}sp"):
            return current
    return None


def get_slide_dimensions(zipf: zipfile.ZipFile) -> tuple[int, int]:
    root = ET.fromstring(zipf.read("ppt/presentation.xml"))
    sld_sz = root.find(".//p:sldSz", NS)
    assert sld_sz is not None, "Missing slide size"
    return int(sld_sz.get("cx")), int(sld_sz.get("cy"))


def get_title_infos(slide: ET.Element) -> list[dict[str, object]]:
    parent_map = build_parent_map(slide)
    infos = []
    for paragraph in slide.findall(".//a:p", NS):
        text = paragraph_text(paragraph)
        if not TITLE_RE.match(text):
            continue
        shape = find_shape_for_paragraph(paragraph, parent_map)
        xfrm = shape.find("p:spPr/a:xfrm", NS) if shape is not None else None
        off = xfrm.find("a:off", NS) if xfrm is not None else None
        ext = xfrm.find("a:ext", NS) if xfrm is not None else None
        infos.append(
            {
                "paragraph": paragraph,
                "text": text,
                "shape": shape,
                "off": off,
                "ext": ext,
            }
        )
    return infos


def collect_non_title_texts(slide: ET.Element) -> list[str]:
    texts = []
    for paragraph in slide.findall(".//a:p", NS):
        text = paragraph_text(paragraph)
        if text and not TITLE_RE.match(text):
            texts.append(text)
    return texts


def assert_run_styled(run: ET.Element) -> None:
    rpr = run.find("a:rPr", NS)
    assert rpr is not None, "Missing run properties"
    assert rpr.get("sz") == "1800", "Expected 18pt font size"
    assert rpr.get("b") in (None, "0"), "Expected bold to be disabled"
    fill = rpr.find("a:solidFill/a:srgbClr", NS)
    assert fill is not None and fill.get("val") == "4F6B8A", "Expected #4F6B8A text color"
    latin = rpr.find("a:latin", NS)
    assert latin is not None and latin.get("typeface") == "Calibri", "Expected Calibri font"
    ea = rpr.find("a:ea", NS)
    if ea is not None:
        assert ea.get("typeface") == "Calibri"
    cs = rpr.find("a:cs", NS)
    if cs is not None:
        assert cs.get("typeface") == "Calibri"


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "Processed PPTX was not created"
    assert OUTPUT_PPTX.stat().st_size > 0, "Processed PPTX is empty"


def test_each_content_slide_has_exactly_one_session_title() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        assert len(slide_names) == 7, "Expected exactly 7 slides after processing"
        for slide_idx in range(2, 7):
            infos = get_title_infos(load_slide(zipf, slide_names, slide_idx))
            assert len(infos) == 1, f"Slide {slide_idx} should have exactly one session title"
            assert infos[0]["text"] == GT_TITLES[slide_idx], f"Unexpected title on slide {slide_idx}"


def test_session_titles_have_required_style() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_idx in range(2, 7):
            info = get_title_infos(load_slide(zipf, slide_names, slide_idx))[0]
            runs = info["paragraph"].findall("a:r", NS)
            assert runs, f"Slide {slide_idx} title has no runs"
            for run in runs:
                assert_run_styled(run)


def test_session_titles_are_single_line_bottom_centered() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_width, slide_height = get_slide_dimensions(zipf)
        slide_names = iter_slide_names(zipf)
        for slide_idx in range(2, 7):
            info = get_title_infos(load_slide(zipf, slide_names, slide_idx))[0]
            paragraph = info["paragraph"]
            ppr = paragraph.find("a:pPr", NS)
            assert ppr is not None and ppr.get("algn") == "ctr", f"Slide {slide_idx} title should be center aligned"

            text = info["text"]
            assert "\n" not in text, f"Slide {slide_idx} title should be on one line"

            off = info["off"]
            ext = info["ext"]
            assert off is not None and ext is not None, f"Slide {slide_idx} title shape is missing geometry"
            x = int(off.get("x"))
            y = int(off.get("y"))
            w = int(ext.get("cx"))
            h = int(ext.get("cy"))

            approx_char_width = int((1800 * 127) * 0.48)
            estimated_width = len(text) * approx_char_width
            assert w >= estimated_width, f"Slide {slide_idx} title box is too narrow"

            left_gap = x
            right_gap = slide_width - (x + w)
            assert abs(left_gap - right_gap) <= slide_width * 0.05, f"Slide {slide_idx} title box should be horizontally centered"

            min_y = int(slide_height * 0.75)
            max_y = slide_height - h
            assert min_y <= y <= max_y, f"Slide {slide_idx} title should be placed near the bottom"

            shape = info["shape"]
            body_pr = shape.find("p:txBody/a:bodyPr", NS) if shape is not None else None
            assert body_pr is not None, f"Slide {slide_idx} title shape is missing body properties"
            assert (body_pr.get("lIns") or "0") == (body_pr.get("rIns") or "0"), f"Slide {slide_idx} title should have balanced text insets"


def test_other_content_is_unchanged() -> None:
    with zipfile.ZipFile(INPUT_PPTX, "r") as zipf_in, zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf_out:
        slide_names_in = iter_slide_names(zipf_in)
        slide_names_out = iter_slide_names(zipf_out)
        for slide_idx in range(1, 7):
            slide_in = load_slide(zipf_in, slide_names_in, slide_idx)
            slide_out = load_slide(zipf_out, slide_names_out, slide_idx)
            assert collect_non_title_texts(slide_in) == collect_non_title_texts(slide_out), f"Slide {slide_idx} non-title content changed"


def test_session_index_slide_exists_and_is_last() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        last_slide = load_slide(zipf, slide_names, 7)
        texts = [paragraph_text(p) for p in last_slide.findall(".//a:p", NS) if paragraph_text(p)]
        assert texts[0] == "Session Index", "Last slide title should be Session Index"


def test_session_index_uses_numbered_unique_sorted_entries() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        last_slide = load_slide(zipf, slide_names, 7)

    bullet_titles = []
    for paragraph in last_slide.findall(".//a:p", NS):
        text = paragraph_text(paragraph)
        if not text or text == "Session Index":
            continue
        ppr = paragraph.find("a:pPr", NS)
        assert ppr is not None, "Session Index entries should have paragraph properties"
        assert ppr.find("a:buAutoNum", NS) is not None, "Session Index entries must use auto-numbered bullets"
        bullet_titles.append(text)

    assert bullet_titles == GT_INDEX, "Session Index entries should be unique and sorted by session number"
    assert len(bullet_titles) == len(set(bullet_titles)), "Session Index contains duplicates"
