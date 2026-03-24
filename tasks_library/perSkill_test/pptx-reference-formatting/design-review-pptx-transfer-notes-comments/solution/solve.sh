#!/bin/bash
set -euo pipefail

python3 <<'PY'
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

INPUT_PPTX = Path(os.environ.get("INPUT_PPTX", "/root/Design-Review-Deck.pptx"))
UPDATES_JSON = Path(os.environ.get("UPDATES_JSON", "/root/design_review_updates.json"))
OUTPUT_PPTX = Path(os.environ.get("OUTPUT_PPTX", "/root/Design-Review-Commented.pptx"))

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}

ET.register_namespace("a", NS["a"])
ET.register_namespace("p", NS["p"])
ET.register_namespace("r", NS["r"])
ET.register_namespace("", NS["rel"])
ET.register_namespace("", NS["ct"])


def paragraph_text(paragraph: ET.Element) -> str:
    return " ".join("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).split())


def set_text_body(shape: ET.Element, paragraphs: list[str], *, bulleted: bool = False) -> None:
    tx_body = shape.find("p:txBody", NS)
    if tx_body is None:
        tx_body = ET.SubElement(shape, f"{{{NS['p']}}}txBody")
        ET.SubElement(tx_body, f"{{{NS['a']}}}bodyPr")
        ET.SubElement(tx_body, f"{{{NS['a']}}}lstStyle")

    body_pr = tx_body.find("a:bodyPr", NS)
    lst_style = tx_body.find("a:lstStyle", NS)
    for child in list(tx_body):
        if child is not body_pr and child is not lst_style:
            tx_body.remove(child)

    if body_pr is None:
        body_pr = ET.Element(f"{{{NS['a']}}}bodyPr")
        tx_body.insert(0, body_pr)
    if lst_style is None:
        lst_style = ET.Element(f"{{{NS['a']}}}lstStyle")
        tx_body.insert(1, lst_style)

    for text in paragraphs:
        paragraph = ET.SubElement(tx_body, f"{{{NS['a']}}}p")
        if bulleted:
            ppr = ET.SubElement(paragraph, f"{{{NS['a']}}}pPr", {"marL": "457200", "indent": "-228600"})
            ET.SubElement(ppr, f"{{{NS['a']}}}buChar", {"char": "•"})
        run = ET.SubElement(paragraph, f"{{{NS['a']}}}r")
        ET.SubElement(run, f"{{{NS['a']}}}rPr", {"lang": "en-US", "dirty": "0"})
        text_node = ET.SubElement(run, f"{{{NS['a']}}}t")
        text_node.text = text
        ET.SubElement(paragraph, f"{{{NS['a']}}}endParaRPr", {"lang": "en-US", "dirty": "0"})


def find_shape_by_text(slide_root: ET.Element, exact_text: str) -> ET.Element:
    for shape in slide_root.findall(".//p:sp", NS):
        texts = [paragraph_text(paragraph) for paragraph in shape.findall(".//a:p", NS)]
        joined = " ".join(text for text in texts if text)
        if joined == exact_text:
            return shape
    raise RuntimeError(f"Unable to find shape with text: {exact_text}")


def get_callout_position(slide_root: ET.Element, label: str) -> tuple[int, int]:
    shape = find_shape_by_text(slide_root, label)
    xfrm = shape.find("p:spPr/a:xfrm", NS)
    if xfrm is None:
        raise RuntimeError(f"Shape {label!r} is missing transform data")
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        raise RuntimeError(f"Shape {label!r} is missing offset/extent")
    x = int(off.get("x"))
    y = int(off.get("y"))
    w = int(ext.get("cx"))
    return x + w + 180000, max(0, y - 120000)


def write_xml(path: Path, root: ET.Element) -> None:
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def update_notes(workspace: Path, notes_by_slide: dict[str, list[str]]) -> None:
    for slide_num, paragraphs in notes_by_slide.items():
        note_path = workspace / "ppt" / "notesSlides" / f"notesSlide{slide_num}.xml"
        root = ET.parse(note_path).getroot()
        shapes = root.findall(".//p:sp", NS)
        if not shapes:
            raise RuntimeError(f"Missing notes text shape for slide {slide_num}")
        set_text_body(shapes[0], paragraphs, bulleted=False)
        write_xml(note_path, root)


def update_comment_authors(workspace: Path, comments: list[dict[str, object]]) -> dict[tuple[str, str], int]:
    author_ids: dict[tuple[str, str], int] = {}
    counts: dict[tuple[str, str], int] = {}
    ordered_authors: list[tuple[str, str]] = []

    for item in comments:
        key = (str(item["author_name"]), str(item["author_initials"]))
        if key not in author_ids:
            author_ids[key] = len(author_ids)
            ordered_authors.append(key)
        counts[key] = counts.get(key, 0) + 1

    root = ET.Element(f"{{{NS['p']}}}cmAuthorLst")
    for index, key in enumerate(ordered_authors):
        name, initials = key
        ET.SubElement(
            root,
            f"{{{NS['p']}}}cmAuthor",
            {
                "id": str(author_ids[key]),
                "name": name,
                "initials": initials,
                "lastIdx": str(counts[key]),
                "clrIdx": str(index % 6),
            },
        )

    write_xml(workspace / "ppt" / "commentAuthors.xml", root)
    return author_ids


def update_comments(workspace: Path, comments: list[dict[str, object]], author_ids: dict[tuple[str, str], int]) -> None:
    by_slide: dict[int, dict[str, object]] = {int(item["slide"]): item for item in comments}

    for slide_num, item in by_slide.items():
        slide_root = ET.parse(workspace / "ppt" / "slides" / f"slide{slide_num}.xml").getroot()
        pos_x, pos_y = get_callout_position(slide_root, str(item["target_label"]))
        author_key = (str(item["author_name"]), str(item["author_initials"]))
        cm_root = ET.Element(f"{{{NS['p']}}}cmLst")
        comment = ET.SubElement(
            cm_root,
            f"{{{NS['p']}}}cm",
            {
                "authorId": str(author_ids[author_key]),
                "dt": "2026-03-22T09:00:00Z",
                "idx": "1",
            },
        )
        ET.SubElement(comment, f"{{{NS['p']}}}pos", {"x": str(pos_x), "y": str(pos_y)})
        text_node = ET.SubElement(comment, f"{{{NS['p']}}}text")
        text_node.text = str(item["text"])
        write_xml(workspace / "ppt" / "comments" / f"comment{slide_num}.xml", cm_root)


def append_action_items_slide(workspace: Path, updates: dict[str, object]) -> None:
    slides_dir = workspace / "ppt" / "slides"
    slide_numbers = sorted(int(path.stem.replace("slide", "")) for path in slides_dir.glob("slide*.xml"))
    next_slide_num = max(slide_numbers) + 1

    template_slide = ET.parse(slides_dir / "slide5.xml").getroot()
    shapes = template_slide.findall(".//p:cSld/p:spTree/p:sp", NS)
    if len(shapes) < 2:
        raise RuntimeError("Unexpected template slide structure")

    sp_tree = template_slide.find(".//p:cSld/p:spTree", NS)
    for shape in list(sp_tree.findall("p:sp", NS))[2:]:
        sp_tree.remove(shape)

    set_text_body(shapes[0], [str(updates["action_items_title"])], bulleted=False)
    bullet_lines = [
        f"{item['owner']}: {item['decision']}"
        for item in updates["action_items"]
    ]
    set_text_body(shapes[1], bullet_lines, bulleted=True)

    slide_path = slides_dir / f"slide{next_slide_num}.xml"
    write_xml(slide_path, template_slide)

    rels_root = ET.Element(f"{{{NS['rel']}}}Relationships")
    ET.SubElement(
        rels_root,
        f"{{{NS['rel']}}}Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout",
            "Target": "../slideLayouts/slideLayout2.xml",
        },
    )
    slide_rels_dir = slides_dir / "_rels"
    slide_rels_dir.mkdir(exist_ok=True)
    write_xml(slide_rels_dir / f"slide{next_slide_num}.xml.rels", rels_root)

    presentation_path = workspace / "ppt" / "presentation.xml"
    presentation_root = ET.parse(presentation_path).getroot()
    sld_id_list = presentation_root.find("p:sldIdLst", NS)
    existing_ids = [int(node.get("id")) for node in sld_id_list.findall("p:sldId", NS)]

    presentation_rels_path = workspace / "ppt" / "_rels" / "presentation.xml.rels"
    presentation_rels = ET.parse(presentation_rels_path).getroot()
    rel_ids = [
        int(rel.get("Id")[3:])
        for rel in presentation_rels.findall("rel:Relationship", NS)
        if rel.get("Id", "").startswith("rId")
    ]
    new_rel_id = f"rId{max(rel_ids) + 1}"
    ET.SubElement(
        presentation_rels,
        f"{{{NS['rel']}}}Relationship",
        {
            "Id": new_rel_id,
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
            "Target": f"slides/slide{next_slide_num}.xml",
        },
    )
    write_xml(presentation_rels_path, presentation_rels)

    ET.SubElement(
        sld_id_list,
        f"{{{NS['p']}}}sldId",
        {
            "id": str(max(existing_ids) + 1),
            f"{{{NS['r']}}}id": new_rel_id,
        },
    )
    write_xml(presentation_path, presentation_root)

    content_types_path = workspace / "[Content_Types].xml"
    content_types = ET.parse(content_types_path).getroot()
    existing_parts = {node.get("PartName") for node in content_types.findall("ct:Override", NS)}
    new_part = f"/ppt/slides/slide{next_slide_num}.xml"
    if new_part not in existing_parts:
        ET.SubElement(
            content_types,
            f"{{{NS['ct']}}}Override",
            {
                "PartName": new_part,
                "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
            },
        )
    write_xml(content_types_path, content_types)


def repack(workspace: Path, output_path: Path) -> None:
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zipf:
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                zipf.write(path, path.relative_to(workspace).as_posix())


updates = json.loads(UPDATES_JSON.read_text())

with tempfile.TemporaryDirectory() as temp_dir:
    workspace = Path(temp_dir)
    with ZipFile(INPUT_PPTX) as zipf:
        zipf.extractall(workspace)

    update_notes(workspace, updates["notes"])
    author_ids = update_comment_authors(workspace, updates["comments"])
    update_comments(workspace, updates["comments"], author_ids)
    append_action_items_slide(workspace, updates)
    repack(workspace, OUTPUT_PPTX)
PY
