from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

INPUT_PPTX = Path("/root/Case-Study-Credits.pptx")
OUTPUT_PPTX = Path("/root/Case-Study-Credits-cleaned.pptx")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
CREDIT_RE = re.compile(r"^(Photo by .+|Image credit: .+)$")


def normalize(text: str) -> str:
    return " ".join(text.split())


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else -1

    return sorted(
        (name for name in zipf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
        key=slide_number,
    )


def load_slide(zipf: zipfile.ZipFile, slide_name: str) -> ET.Element:
    return ET.fromstring(zipf.read(slide_name))


def paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.findall(".//a:t", NS))


def build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def find_shape(node: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = node
    while current in parent_map:
        current = parent_map[current]
        if current.tag.endswith("}sp"):
            return current
    return None


def get_slide_dimensions(zipf: zipfile.ZipFile) -> tuple[int, int]:
    root = ET.fromstring(zipf.read("ppt/presentation.xml"))
    size = root.find(".//p:sldSz", NS)
    assert size is not None, "presentation.xml is missing slide size"
    return int(size.get("cx")), int(size.get("cy"))


def collect_expected_credits(zipf: zipfile.ZipFile) -> list[tuple[int, str]]:
    credits: list[tuple[int, str]] = []
    for idx, slide_name in enumerate(iter_slide_names(zipf), start=1):
        slide = load_slide(zipf, slide_name)
        for paragraph in slide.findall(".//a:p", NS):
            text = normalize(paragraph_text(paragraph))
            if CREDIT_RE.fullmatch(text):
                credits.append((idx, text))
    return credits


def unique_in_order(items: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def find_credit_infos(slide: ET.Element) -> list[dict[str, ET.Element | str]]:
    parent_map = build_parent_map(slide)
    infos: list[dict[str, ET.Element | str]] = []
    for paragraph in slide.findall(".//a:p", NS):
        text = normalize(paragraph_text(paragraph))
        if not CREDIT_RE.fullmatch(text):
            continue
        shape = find_shape(paragraph, parent_map)
        if shape is None:
            continue
        xfrm = shape.find("p:spPr/a:xfrm", NS)
        off = xfrm.find("a:off", NS) if xfrm is not None else None
        ext = xfrm.find("a:ext", NS) if xfrm is not None else None
        infos.append(
            {
                "text": text,
                "paragraph": paragraph,
                "shape": shape,
                "off": off,
                "ext": ext,
            }
        )
    return infos


def assert_credit_run_style(run: ET.Element) -> None:
    rpr = run.find("a:rPr", NS)
    assert rpr is not None, "credit run is missing rPr"
    assert rpr.get("sz") == "1200", "credit font size must be 12pt"
    assert rpr.get("i") == "1", "credit text must be italic"
    solid = rpr.find("a:solidFill/a:srgbClr", NS)
    assert solid is not None and solid.get("val") == "4A4A4A", "credit color must be #4A4A4A"
    for tag in ("latin", "ea", "cs"):
        node = rpr.find(f"a:{tag}", NS)
        assert node is not None and node.get("typeface") == "Calibri", "credit font must be Calibri"


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "expected cleaned deck at /root/Case-Study-Credits-cleaned.pptx"
    assert OUTPUT_PPTX.stat().st_size > 0, "output deck is empty"


def test_each_original_credit_is_preserved_on_its_slide() -> None:
    with zipfile.ZipFile(INPUT_PPTX) as input_zip, zipfile.ZipFile(OUTPUT_PPTX) as output_zip:
        expected = collect_expected_credits(input_zip)
        output_slide_names = iter_slide_names(output_zip)
        assert len(output_slide_names) == len(iter_slide_names(input_zip)) + 1, "expected one appended credits slide"
        for slide_index, credit in expected:
            slide = load_slide(output_zip, output_slide_names[slide_index - 1])
            infos = find_credit_infos(slide)
            assert len(infos) == 1, f"slide {slide_index} should contain exactly one formatted footer credit"
            assert infos[0]["text"] == credit, f"slide {slide_index} credit text changed unexpectedly"


def test_credit_footers_match_required_style_and_position() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX) as output_zip:
        slide_width, slide_height = get_slide_dimensions(output_zip)
        for slide_name in iter_slide_names(output_zip)[:-1]:
            slide = load_slide(output_zip, slide_name)
            for info in find_credit_infos(slide):
                paragraph = info["paragraph"]
                ppr = paragraph.find("a:pPr", NS)
                assert ppr is not None and ppr.get("algn") == "r", "credit paragraph must be right aligned"
                assert "\n" not in paragraph_text(paragraph), "credit footer must stay on one line"

                body_pr = info["shape"].find("p:txBody/a:bodyPr", NS)
                assert body_pr is not None, "credit shape is missing bodyPr"
                assert body_pr.get("wrap") == "none", "credit footer should disable wrapping"

                runs = paragraph.findall("a:r", NS)
                assert runs, "credit paragraph must contain a run"
                for run in runs:
                    assert_credit_run_style(run)

                off = info["off"]
                ext = info["ext"]
                assert off is not None and ext is not None, "credit footer needs explicit geometry"
                x = int(off.get("x"))
                y = int(off.get("y"))
                w = int(ext.get("cx"))
                h = int(ext.get("cy"))
                assert x > int(slide_width * 0.55), "credit footer should sit in the right side of the slide"
                assert x + w >= int(slide_width * 0.92), "credit footer should extend to the right edge area"
                assert y > int(slide_height * 0.84), "credit footer should sit near the bottom edge"
                assert h <= 300000, "credit footer height should stay compact for one line"


def test_summary_slide_has_deduplicated_ordered_credits() -> None:
    with zipfile.ZipFile(INPUT_PPTX) as input_zip, zipfile.ZipFile(OUTPUT_PPTX) as output_zip:
        expected_unique = unique_in_order([credit for _, credit in collect_expected_credits(input_zip)])
        summary_slide = load_slide(output_zip, iter_slide_names(output_zip)[-1])

        title_texts = [normalize(paragraph_text(p)) for p in summary_slide.findall(".//a:p", NS)]
        assert "Image Credits" in title_texts, "last slide must be titled Image Credits"

        numbered_items: list[str] = []
        for paragraph in summary_slide.findall(".//a:p", NS):
            ppr = paragraph.find("a:pPr", NS)
            if ppr is None or ppr.find("a:buAutoNum", NS) is None:
                continue
            numbered_items.append(normalize(paragraph_text(paragraph)))

        assert numbered_items == expected_unique, "Image Credits slide should list unique credits in first-appearance order"
