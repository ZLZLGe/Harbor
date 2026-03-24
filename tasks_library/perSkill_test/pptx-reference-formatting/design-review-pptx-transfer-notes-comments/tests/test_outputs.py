from __future__ import annotations

import json
import os
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

INPUT_PPTX = Path(os.environ.get("INPUT_PPTX", "/root/Design-Review-Deck.pptx"))
UPDATES_JSON = Path(os.environ.get("UPDATES_JSON", "/root/design_review_updates.json"))
OUTPUT_PPTX = Path(os.environ.get("OUTPUT_PPTX", "/root/Design-Review-Commented.pptx"))

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def load_updates() -> dict:
    return json.loads(UPDATES_JSON.read_text())


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        (name for name in zipf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name)),
        key=slide_number,
    )


def slide_root(zipf: zipfile.ZipFile, slide_name: str) -> ET.Element:
    return ET.fromstring(zipf.read(slide_name))


def paragraph_text(paragraph: ET.Element) -> str:
    return " ".join("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).split())


def slide_texts(slide: ET.Element) -> list[str]:
    texts = []
    for paragraph in slide.findall(".//a:p", NS):
        text = paragraph_text(paragraph)
        if text:
            texts.append(text)
    return texts


def slide_visible_texts(zipf: zipfile.ZipFile) -> list[list[str]]:
    return [slide_texts(slide_root(zipf, name)) for name in iter_slide_names(zipf)]


def resolve_rel_target(zipf: zipfile.ZipFile, part_name: str, rel_type_suffix: str) -> str:
    rel_name = posixpath.join(
        posixpath.dirname(part_name),
        "_rels",
        posixpath.basename(part_name) + ".rels",
    )
    rel_root = ET.fromstring(zipf.read(rel_name))
    for rel in rel_root.findall("rel:Relationship", NS):
        if rel.get("Type", "").endswith(rel_type_suffix):
            target = rel.get("Target")
            assert target, f"Missing relationship target for {rel_type_suffix}"
            return posixpath.normpath(posixpath.join(posixpath.dirname(part_name), target))
    raise AssertionError(f"Missing {rel_type_suffix} relationship for {part_name}")


def note_paragraphs(zipf: zipfile.ZipFile, slide_name: str) -> list[str]:
    note_path = resolve_rel_target(zipf, slide_name, "/notesSlide")
    root = ET.fromstring(zipf.read(note_path))
    texts = []
    for paragraph in root.findall(".//a:p", NS):
        text = paragraph_text(paragraph)
        if text:
            texts.append(text)
    return texts


def comment_payload(zipf: zipfile.ZipFile, slide_name: str) -> list[dict[str, object]]:
    comment_path = resolve_rel_target(zipf, slide_name, "/comments")
    root = ET.fromstring(zipf.read(comment_path))
    payload = []
    for node in root.findall("p:cm", NS):
        pos = node.find("p:pos", NS)
        payload.append(
            {
                "author_id": int(node.get("authorId")),
                "idx": int(node.get("idx")),
                "text": node.findtext("p:text", default="", namespaces=NS),
                "x": int(pos.get("x")) if pos is not None else None,
                "y": int(pos.get("y")) if pos is not None else None,
            }
        )
    return payload


def comment_authors(zipf: zipfile.ZipFile) -> dict[int, dict[str, str]]:
    root = ET.fromstring(zipf.read("ppt/commentAuthors.xml"))
    authors: dict[int, dict[str, str]] = {}
    for node in root.findall("p:cmAuthor", NS):
        authors[int(node.get("id"))] = {
            "name": node.get("name", ""),
            "initials": node.get("initials", ""),
            "lastIdx": node.get("lastIdx", ""),
        }
    return authors


def find_shape_by_text(slide: ET.Element, exact_text: str) -> ET.Element:
    for shape in slide.findall(".//p:sp", NS):
        texts = [paragraph_text(paragraph) for paragraph in shape.findall(".//a:p", NS)]
        joined = " ".join(text for text in texts if text)
        if joined == exact_text:
            return shape
    raise AssertionError(f"Unable to find shape with text {exact_text!r}")


def shape_bounds(shape: ET.Element) -> tuple[int, int, int, int]:
    xfrm = shape.find("p:spPr/a:xfrm", NS)
    assert xfrm is not None, "Shape is missing transform data"
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    assert off is not None and ext is not None, "Shape is missing offset or extent"
    return (
        int(off.get("x")),
        int(off.get("y")),
        int(ext.get("cx")),
        int(ext.get("cy")),
    )


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "Expected output presentation to be created"
    assert OUTPUT_PPTX.stat().st_size > 0, "Output presentation is empty"


def test_original_slide_content_is_preserved_and_one_slide_is_appended() -> None:
    with zipfile.ZipFile(INPUT_PPTX, "r") as input_zip, zipfile.ZipFile(OUTPUT_PPTX, "r") as output_zip:
        input_slides = slide_visible_texts(input_zip)
        output_slides = slide_visible_texts(output_zip)

    assert len(input_slides) == 6, "Unexpected input slide count"
    assert len(output_slides) == 7, "Expected one new slide to be appended"
    assert output_slides[:6] == input_slides, "Visible content on the original slides changed"


def test_speaker_notes_match_json_and_stale_text_is_removed() -> None:
    updates = load_updates()
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_num, expected in updates["notes"].items():
            actual = note_paragraphs(zipf, slide_names[int(slide_num) - 1])
            assert actual == expected, f"Unexpected speaker notes on slide {slide_num}"
            joined = "\n".join(actual)
            assert "TODO: replace with final presenter notes." not in joined
            assert "Stale review note: remove before Friday." not in joined


def test_comment_authors_and_comment_texts_match_json() -> None:
    updates = load_updates()
    expected_by_slide = {item["slide"]: item for item in updates["comments"]}

    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        authors = comment_authors(zipf)

        assert len(authors) == 3, "Expected exactly three unique reviewer authors"

        for slide_num, expected in expected_by_slide.items():
            comments = comment_payload(zipf, slide_names[slide_num - 1])
            assert len(comments) == 1, f"Expected one reviewer comment on slide {slide_num}"
            comment = comments[0]
            author = authors[comment["author_id"]]
            assert author["name"] == expected["author_name"]
            assert author["initials"] == expected["author_initials"]
            assert comment["text"] == expected["text"]
            assert "Stale reviewer comment" not in comment["text"]


def test_comments_are_positioned_near_the_target_labels() -> None:
    updates = load_updates()
    expected_by_slide = {item["slide"]: item for item in updates["comments"]}

    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_num, expected in expected_by_slide.items():
            slide = slide_root(zipf, slide_names[slide_num - 1])
            comment = comment_payload(zipf, slide_names[slide_num - 1])[0]
            shape = find_shape_by_text(slide, expected["target_label"])
            x, y, w, _ = shape_bounds(shape)
            expected_x = x + w + 180000
            expected_y = max(0, y - 120000)
            assert abs(comment["x"] - expected_x) <= 20000, f"Comment x-position is off on slide {slide_num}"
            assert abs(comment["y"] - expected_y) <= 20000, f"Comment y-position is off on slide {slide_num}"


def test_action_items_slide_is_last_and_uses_real_bullets() -> None:
    updates = load_updates()
    expected_lines = [f"{item['owner']}: {item['decision']}" for item in updates["action_items"]]

    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        last_slide = slide_root(zipf, slide_names[-1])
        paragraphs = [paragraph for paragraph in last_slide.findall(".//a:p", NS) if paragraph_text(paragraph)]

    assert paragraph_text(paragraphs[0]) == updates["action_items_title"], "Unexpected Action Items slide title"
    actual_lines = [paragraph_text(paragraph) for paragraph in paragraphs[1:]]
    assert actual_lines == expected_lines, "Unexpected action-item lines"

    for paragraph in paragraphs[1:]:
        ppr = paragraph.find("a:pPr", NS)
        assert ppr is not None, "Action item paragraph is missing paragraph properties"
        assert ppr.find("a:buChar", NS) is not None, "Action items must use real bullet formatting"
