#!/bin/bash
set -euo pipefail

python3 <<'PY'
from __future__ import annotations

import json
import os
import posixpath
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

INPUT_PPTX = Path(os.environ.get("INPUT_PPTX", "/root/Webinar-Rehearsal.pptx"))
NOTES_JSON = Path(os.environ.get("NOTES_JSON", "/root/speaker_notes.json"))
OUTPUT_PPTX = Path(os.environ.get("OUTPUT_PPTX", "/root/Webinar-Rehearsal-notes-ready.pptx"))

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

NOTES_MASTER_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:notesMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="Notes Master">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:hf/>
  <p:notesStyle/>
</p:notesMaster>
"""

NOTES_MASTER_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""


def write_xml(path: Path, root: ET.Element) -> None:
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def next_rid(root: ET.Element) -> str:
    numbers = [
        int(rel.get("Id")[3:])
        for rel in root.findall("rel:Relationship", NS)
        if rel.get("Id", "").startswith("rId")
    ]
    return f"rId{max(numbers, default=0) + 1}"


def ensure_content_type(workspace: Path, part_name: str, content_type: str) -> None:
    content_types_path = workspace / "[Content_Types].xml"
    root = ET.parse(content_types_path).getroot()
    existing = {node.get("PartName") for node in root.findall("ct:Override", NS)}
    if part_name not in existing:
        ET.SubElement(
            root,
            f"{{{NS['ct']}}}Override",
            {"PartName": part_name, "ContentType": content_type},
        )
        write_xml(content_types_path, root)


def ensure_notes_master(workspace: Path) -> None:
    notes_master_path = workspace / "ppt" / "notesMasters" / "notesMaster1.xml"
    notes_master_rels_path = workspace / "ppt" / "notesMasters" / "_rels" / "notesMaster1.xml.rels"
    notes_master_path.parent.mkdir(parents=True, exist_ok=True)
    notes_master_rels_path.parent.mkdir(parents=True, exist_ok=True)

    if not notes_master_path.exists():
        notes_master_path.write_text(NOTES_MASTER_XML, encoding="utf-8")
    if not notes_master_rels_path.exists():
        notes_master_rels_path.write_text(NOTES_MASTER_RELS_XML, encoding="utf-8")

    pres_rels_path = workspace / "ppt" / "_rels" / "presentation.xml.rels"
    pres_rels_root = ET.parse(pres_rels_path).getroot()
    if not any(rel.get("Type", "").endswith("/notesMaster") for rel in pres_rels_root.findall("rel:Relationship", NS)):
        ET.SubElement(
            pres_rels_root,
            f"{{{NS['rel']}}}Relationship",
            {
                "Id": next_rid(pres_rels_root),
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster",
                "Target": "notesMasters/notesMaster1.xml",
            },
        )
        write_xml(pres_rels_path, pres_rels_root)

    ensure_content_type(
        workspace,
        "/ppt/notesMasters/notesMaster1.xml",
        "application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml",
    )


def resolve_target(base_part: str, target: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(base_part), target))


def find_notes_part(workspace: Path, slide_num: int) -> Path | None:
    slide_rel_path = workspace / "ppt" / "slides" / "_rels" / f"slide{slide_num}.xml.rels"
    rel_root = ET.parse(slide_rel_path).getroot()
    for rel in rel_root.findall("rel:Relationship", NS):
        if rel.get("Type", "").endswith("/notesSlide"):
            part = resolve_target(f"ppt/slides/slide{slide_num}.xml", rel.get("Target", ""))
            return workspace / part
    return None


def create_empty_notes_slide_xml() -> ET.Element:
    root = ET.Element(f"{{{NS['p']}}}notes")
    c_sld = ET.SubElement(root, f"{{{NS['p']}}}cSld")
    sp_tree = ET.SubElement(c_sld, f"{{{NS['p']}}}spTree")

    nv_grp = ET.SubElement(sp_tree, f"{{{NS['p']}}}nvGrpSpPr")
    ET.SubElement(nv_grp, f"{{{NS['p']}}}cNvPr", {"id": "1", "name": ""})
    ET.SubElement(nv_grp, f"{{{NS['p']}}}cNvGrpSpPr")
    ET.SubElement(nv_grp, f"{{{NS['p']}}}nvPr")

    grp = ET.SubElement(sp_tree, f"{{{NS['p']}}}grpSpPr")
    xfrm = ET.SubElement(grp, f"{{{NS['a']}}}xfrm")
    ET.SubElement(xfrm, f"{{{NS['a']}}}off", {"x": "0", "y": "0"})
    ET.SubElement(xfrm, f"{{{NS['a']}}}ext", {"cx": "0", "cy": "0"})
    ET.SubElement(xfrm, f"{{{NS['a']}}}chOff", {"x": "0", "y": "0"})
    ET.SubElement(xfrm, f"{{{NS['a']}}}chExt", {"cx": "0", "cy": "0"})

    shape = ET.SubElement(sp_tree, f"{{{NS['p']}}}sp")
    nv_sp = ET.SubElement(shape, f"{{{NS['p']}}}nvSpPr")
    ET.SubElement(nv_sp, f"{{{NS['p']}}}cNvPr", {"id": "2", "name": "Notes Placeholder 1"})
    ET.SubElement(nv_sp, f"{{{NS['p']}}}cNvSpPr", {"txBox": "1"})
    nv_pr = ET.SubElement(nv_sp, f"{{{NS['p']}}}nvPr")
    ET.SubElement(nv_pr, f"{{{NS['p']}}}ph", {"type": "body", "idx": "1"})
    ET.SubElement(shape, f"{{{NS['p']}}}spPr")

    tx_body = ET.SubElement(shape, f"{{{NS['p']}}}txBody")
    ET.SubElement(tx_body, f"{{{NS['a']}}}bodyPr")
    ET.SubElement(tx_body, f"{{{NS['a']}}}lstStyle")

    clr_map = ET.SubElement(root, f"{{{NS['p']}}}clrMapOvr")
    ET.SubElement(clr_map, f"{{{NS['a']}}}masterClrMapping")
    return root


def set_paragraphs(shape: ET.Element, title: str, bullets: list[str]) -> None:
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

    def add_paragraph(text: str, *, bulleted: bool) -> None:
        paragraph = ET.SubElement(tx_body, f"{{{NS['a']}}}p")
        if bulleted:
            ppr = ET.SubElement(
                paragraph,
                f"{{{NS['a']}}}pPr",
                {"marL": "457200", "indent": "-228600"},
            )
            ET.SubElement(ppr, f"{{{NS['a']}}}buChar", {"char": "•"})
        run = ET.SubElement(paragraph, f"{{{NS['a']}}}r")
        ET.SubElement(run, f"{{{NS['a']}}}rPr", {"lang": "en-US", "dirty": "0"})
        text_node = ET.SubElement(run, f"{{{NS['a']}}}t")
        text_node.text = text
        ET.SubElement(paragraph, f"{{{NS['a']}}}endParaRPr", {"lang": "en-US", "dirty": "0"})

    add_paragraph(title, bulleted=False)
    for bullet in bullets:
        add_paragraph(bullet, bulleted=True)


def ensure_notes_slide(workspace: Path, slide_num: int) -> Path:
    ensure_notes_master(workspace)
    slide_rel_path = workspace / "ppt" / "slides" / "_rels" / f"slide{slide_num}.xml.rels"
    rel_root = ET.parse(slide_rel_path).getroot()
    notes_path = find_notes_part(workspace, slide_num)
    if notes_path is None:
        notes_path = workspace / "ppt" / "notesSlides" / f"notesSlide{slide_num}.xml"
        ET.SubElement(
            rel_root,
            f"{{{NS['rel']}}}Relationship",
            {
                "Id": next_rid(rel_root),
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide",
                "Target": f"../notesSlides/notesSlide{slide_num}.xml",
            },
        )
        write_xml(slide_rel_path, rel_root)

    notes_path.parent.mkdir(parents=True, exist_ok=True)
    (notes_path.parent / "_rels").mkdir(exist_ok=True)

    if not notes_path.exists():
        write_xml(notes_path, create_empty_notes_slide_xml())

    notes_rels_path = notes_path.parent / "_rels" / f"{notes_path.name}.rels"
    notes_rels_root = ET.Element(f"{{{NS['rel']}}}Relationships")
    ET.SubElement(
        notes_rels_root,
        f"{{{NS['rel']}}}Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
            "Target": f"../slides/slide{slide_num}.xml",
        },
    )
    ET.SubElement(
        notes_rels_root,
        f"{{{NS['rel']}}}Relationship",
        {
            "Id": "rId2",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster",
            "Target": "../notesMasters/notesMaster1.xml",
        },
    )
    write_xml(notes_rels_path, notes_rels_root)

    ensure_content_type(
        workspace,
        f"/ppt/notesSlides/{notes_path.name}",
        "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
    )
    return notes_path


def update_slide_notes(workspace: Path, slide_num: int, title: str, bullets: list[str]) -> None:
    notes_path = ensure_notes_slide(workspace, slide_num)
    root = ET.parse(notes_path).getroot()
    shape = root.find(".//p:sp", NS)
    if shape is None:
        shape = create_empty_notes_slide_xml().find(".//p:sp", NS)
        sp_tree = root.find(".//p:spTree", NS)
        sp_tree.append(shape)
    set_paragraphs(shape, title, bullets)
    write_xml(notes_path, root)


def repack(workspace: Path, output_path: Path) -> None:
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zipf:
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                zipf.write(path, path.relative_to(workspace).as_posix())


notes_spec = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
workspace = Path(tempfile.mkdtemp(prefix="speaker_notes_work_", dir="/tmp"))

with ZipFile(INPUT_PPTX, "r") as zipf:
    zipf.extractall(workspace)

for slide_num_str, payload in sorted(notes_spec["slides"].items(), key=lambda item: int(item[0])):
    update_slide_notes(
        workspace,
        int(slide_num_str),
        str(payload["title"]),
        [str(item) for item in payload["bullets"]],
    )

repack(workspace, OUTPUT_PPTX)
PY
