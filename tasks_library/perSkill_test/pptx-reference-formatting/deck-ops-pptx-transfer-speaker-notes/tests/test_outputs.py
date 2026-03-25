from __future__ import annotations

import json
import os
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

INPUT_PPTX = Path(os.environ.get("INPUT_PPTX", "/root/Webinar-Rehearsal.pptx"))
NOTES_JSON = Path(os.environ.get("NOTES_JSON", "/root/speaker_notes.json"))
OUTPUT_PPTX = Path(os.environ.get("OUTPUT_PPTX", "/root/Webinar-Rehearsal-notes-ready.pptx"))

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def load_notes_spec() -> dict:
    return json.loads(NOTES_JSON.read_text(encoding="utf-8"))


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        (name for name in zipf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
        key=slide_number,
    )


def slide_root(zipf: zipfile.ZipFile, slide_name: str) -> ET.Element:
    return ET.fromstring(zipf.read(slide_name))


def paragraph_text(paragraph: ET.Element) -> str:
    return " ".join("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).split())


def visible_slide_texts(zipf: zipfile.ZipFile) -> list[list[str]]:
    payload: list[list[str]] = []
    for slide_name in iter_slide_names(zipf):
        texts: list[str] = []
        slide = slide_root(zipf, slide_name)
        for paragraph in slide.findall(".//a:p", NS):
            text = paragraph_text(paragraph)
            if text:
                texts.append(text)
        payload.append(texts)
    return payload


def maybe_resolve_rel_target(zipf: zipfile.ZipFile, part_name: str, rel_type_suffix: str) -> str | None:
    rel_name = posixpath.join(
        posixpath.dirname(part_name),
        "_rels",
        posixpath.basename(part_name) + ".rels",
    )
    rel_root = ET.fromstring(zipf.read(rel_name))
    for rel in rel_root.findall("rel:Relationship", NS):
        if rel.get("Type", "").endswith(rel_type_suffix):
            target = rel.get("Target")
            if not target:
                return None
            return posixpath.normpath(posixpath.join(posixpath.dirname(part_name), target))
    return None


def note_paragraphs(zipf: zipfile.ZipFile, slide_name: str) -> list[dict[str, object]]:
    note_path = maybe_resolve_rel_target(zipf, slide_name, "/notesSlide")
    if note_path is None:
        return []

    root = ET.fromstring(zipf.read(note_path))
    payload: list[dict[str, object]] = []
    for paragraph in root.findall(".//p:sp/p:txBody/a:p", NS):
        text = paragraph_text(paragraph)
        if not text:
            continue
        ppr = paragraph.find("a:pPr", NS)
        is_bullet = ppr is not None and ppr.find("a:buChar", NS) is not None
        payload.append({"text": text, "is_bullet": is_bullet})
    return payload


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "expected output deck at /root/Webinar-Rehearsal-notes-ready.pptx"
    assert OUTPUT_PPTX.stat().st_size > 0, "output deck is empty"


def test_visible_slides_are_unchanged() -> None:
    with zipfile.ZipFile(INPUT_PPTX) as input_zip, zipfile.ZipFile(OUTPUT_PPTX) as output_zip:
        assert iter_slide_names(input_zip) == iter_slide_names(output_zip), "slide set changed unexpectedly"
        assert visible_slide_texts(output_zip) == visible_slide_texts(input_zip), "visible slide content changed"


def test_targeted_notes_match_json_contract() -> None:
    notes_spec = load_notes_spec()["slides"]
    stale_markers = {
        "TODO: replace this rehearsal title.",
        "Outdated bullet: remove before the webinar.",
        "OLD TITLE - replace for final run.",
        "Stale reminder: tighten this closing message.",
    }

    with zipfile.ZipFile(OUTPUT_PPTX) as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_num_str, expected in sorted(notes_spec.items(), key=lambda item: int(item[0])):
            slide_name = slide_names[int(slide_num_str) - 1]
            paragraphs = note_paragraphs(zipf, slide_name)
            expected_texts = [expected["title"], *expected["bullets"]]
            actual_texts = [item["text"] for item in paragraphs]
            assert actual_texts == expected_texts, f"unexpected speaker notes on slide {slide_num_str}"

            assert paragraphs[0]["is_bullet"] is False, f"slide {slide_num_str} title paragraph must not be bulleted"
            for item in paragraphs[1:]:
                assert item["is_bullet"] is True, f"slide {slide_num_str} bullet paragraph is missing real bullet formatting"

            assert stale_markers.isdisjoint(actual_texts), f"stale notes remained on slide {slide_num_str}"


def test_only_requested_slides_have_notes() -> None:
    target_slides = {int(key) for key in load_notes_spec()["slides"].keys()}

    with zipfile.ZipFile(OUTPUT_PPTX) as zipf:
        for index, slide_name in enumerate(iter_slide_names(zipf), start=1):
            note_path = maybe_resolve_rel_target(zipf, slide_name, "/notesSlide")
            if index in target_slides:
                assert note_path is not None, f"slide {index} is missing speaker notes"
            else:
                assert note_path is None, f"slide {index} should not have speaker notes"
