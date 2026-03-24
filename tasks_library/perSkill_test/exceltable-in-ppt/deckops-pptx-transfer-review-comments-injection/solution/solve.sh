#!/bin/bash
set -euo pipefail

INPUT_PPTX="${INPUT_PPTX:-/root/compliance-review-deck.pptx}"
OUTPUT_PPTX="${OUTPUT_PPTX:-/root/review-comments-injected.pptx}"
export INPUT_PPTX OUTPUT_PPTX

python3 - <<'PY'
from collections import defaultdict
from pathlib import Path
import os
import re
import zipfile
from xml.etree import ElementTree as ET

INPUT_PPTX = Path(os.environ.get("INPUT_PPTX", "/root/compliance-review-deck.pptx"))
OUTPUT_PPTX = Path(os.environ.get("OUTPUT_PPTX", "/root/review-comments-injected.pptx"))

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PKGREL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("a", A_NS)
ET.register_namespace("p", P_NS)
ET.register_namespace("r", R_NS)
ET.register_namespace("", CT_NS)
ET.register_namespace("", PKGREL_NS)

P = {"a": A_NS, "p": P_NS, "r": R_NS}

LINE_RE = re.compile(r"^S(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.+)$")


def shape_blocks(slide_root):
    for shape in slide_root.findall(".//p:sp", P):
        xfrm = shape.find("./p:spPr/a:xfrm", P)
        tx_body = shape.find("./p:txBody", P)
        if xfrm is None or tx_body is None:
            continue
        paragraphs = []
        for para in tx_body.findall("./a:p", P):
            text = "".join(node.text or "" for node in para.findall(".//a:t", P)).strip()
            if text:
                paragraphs.append(text)
        if not paragraphs:
            continue
        off = xfrm.find("./a:off", P)
        ext = xfrm.find("./a:ext", P)
        if off is None or ext is None:
            continue
        yield {
            "paragraphs": paragraphs,
            "x": int(off.attrib["x"]),
            "y": int(off.attrib["y"]),
            "cx": int(ext.attrib["cx"]),
            "cy": int(ext.attrib["cy"]),
        }


def next_rid(rels_root):
    highest = 0
    for rel in rels_root.findall("{%s}Relationship" % PKGREL_NS):
        rel_id = rel.attrib["Id"]
        if rel_id.startswith("rId"):
            try:
                highest = max(highest, int(rel_id[3:]))
            except ValueError:
                pass
    return f"rId{highest + 1}"


with zipfile.ZipFile(INPUT_PPTX, "r") as zin:
    files = {info.filename: zin.read(info.filename) for info in zin.infolist()}

control_root = ET.fromstring(files["ppt/slides/slide1.xml"])
requests = []
for block in shape_blocks(control_root):
    for line in block["paragraphs"]:
        match = LINE_RE.match(line)
        if not match:
            continue
        slide_no, label, author_name, initials, comment_text = match.groups()
        requests.append(
            {
                "slide_no": int(slide_no),
                "label": label.strip(),
                "author_name": author_name.strip(),
                "initials": initials.strip(),
                "comment_text": comment_text.strip(),
            }
        )

if not requests:
    raise RuntimeError("No review requests were found on slide 1.")

author_ids = {}
author_order = []
author_comment_counts = defaultdict(int)
comments_by_slide = defaultdict(list)

for item in requests:
    author_key = (item["author_name"], item["initials"])
    if author_key not in author_ids:
        author_ids[author_key] = len(author_ids)
        author_order.append(author_key)
    author_id = author_ids[author_key]
    author_comment_counts[author_key] += 1

    slide_path = f"ppt/slides/slide{item['slide_no']}.xml"
    slide_root = ET.fromstring(files[slide_path])
    target = None
    for block in shape_blocks(slide_root):
        if block["paragraphs"][0] == item["label"]:
            target = block
            break
    if target is None:
        raise RuntimeError(f"Could not find target text box '{item['label']}' on slide {item['slide_no']}.")

    margin = 152400
    pos_x = min(target["x"] + target["cx"] - margin, target["x"] + target["cx"] - 1)
    pos_y = min(target["y"] + margin, target["y"] + target["cy"] - 1)

    comments_by_slide[item["slide_no"]].append(
        {
            "author_id": author_id,
            "author_key": author_key,
            "idx": author_comment_counts[author_key],
            "text": item["comment_text"],
            "x": pos_x,
            "y": pos_y,
        }
    )

authors_root = ET.Element(f"{{{P_NS}}}cmAuthorLst")
for color_index, (name, initials) in enumerate(author_order):
    author = ET.SubElement(
        authors_root,
        f"{{{P_NS}}}cmAuthor",
        id=str(author_ids[(name, initials)]),
        name=name,
        initials=initials,
        lastIdx=str(author_comment_counts[(name, initials)]),
        clrIdx=str(color_index),
    )

files["ppt/commentAuthors.xml"] = ET.tostring(authors_root, encoding="utf-8", xml_declaration=True)

ct_root = ET.fromstring(files["[Content_Types].xml"])
existing_overrides = {node.attrib.get("PartName") for node in ct_root.findall(f"{{{CT_NS}}}Override")}
for part_name, content_type in [
    ("/ppt/commentAuthors.xml", "application/vnd.openxmlformats-officedocument.presentationml.commentAuthors+xml"),
]:
    if part_name not in existing_overrides:
        ET.SubElement(ct_root, f"{{{CT_NS}}}Override", PartName=part_name, ContentType=content_type)

presentation_rels = ET.fromstring(files["ppt/_rels/presentation.xml.rels"])
comment_author_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/commentAuthors"
has_comment_author_rel = any(
    rel.attrib.get("Type") == comment_author_type for rel in presentation_rels.findall(f"{{{PKGREL_NS}}}Relationship")
)
if not has_comment_author_rel:
    ET.SubElement(
        presentation_rels,
        f"{{{PKGREL_NS}}}Relationship",
        Id=next_rid(presentation_rels),
        Type=comment_author_type,
        Target="commentAuthors.xml",
    )

comment_part_index = 1
comment_rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
comment_content_type = "application/vnd.openxmlformats-officedocument.presentationml.comments+xml"

for slide_no in sorted(comments_by_slide):
    cm_root = ET.Element(f"{{{P_NS}}}cmLst")
    for comment in comments_by_slide[slide_no]:
        cm = ET.SubElement(
            cm_root,
            f"{{{P_NS}}}cm",
            authorId=str(comment["author_id"]),
            dt="2026-03-19T09:00:00Z",
            idx=str(comment["idx"]),
        )
        ET.SubElement(cm, f"{{{P_NS}}}pos", x=str(comment["x"]), y=str(comment["y"]))
        text_node = ET.SubElement(cm, f"{{{P_NS}}}text")
        text_node.text = comment["text"]

    comment_part = f"ppt/comments/comment{comment_part_index}.xml"
    files[comment_part] = ET.tostring(cm_root, encoding="utf-8", xml_declaration=True)

    part_name = f"/{comment_part}"
    if part_name not in existing_overrides:
        ET.SubElement(ct_root, f"{{{CT_NS}}}Override", PartName=part_name, ContentType=comment_content_type)
        existing_overrides.add(part_name)

    rels_path = f"ppt/slides/_rels/slide{slide_no}.xml.rels"
    rels_root = ET.fromstring(files[rels_path])
    existing_comment_rel = any(
        rel.attrib.get("Type") == comment_rel_type for rel in rels_root.findall(f"{{{PKGREL_NS}}}Relationship")
    )
    if not existing_comment_rel:
        ET.SubElement(
            rels_root,
            f"{{{PKGREL_NS}}}Relationship",
            Id=next_rid(rels_root),
            Type=comment_rel_type,
            Target=f"../comments/comment{comment_part_index}.xml",
        )
    files[rels_path] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
    comment_part_index += 1

files["[Content_Types].xml"] = ET.tostring(ct_root, encoding="utf-8", xml_declaration=True)
files["ppt/_rels/presentation.xml.rels"] = ET.tostring(presentation_rels, encoding="utf-8", xml_declaration=True)

OUTPUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUTPUT_PPTX, "w", zipfile.ZIP_DEFLATED) as zout:
    for name in sorted(files):
        zout.writestr(name, files[name])
PY
