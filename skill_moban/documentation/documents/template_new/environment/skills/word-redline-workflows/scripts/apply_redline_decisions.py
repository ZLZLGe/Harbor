from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REVIEW_NS = "urn:northharbor:review-manifest"
NS = {"w": W_NS, "rv": REVIEW_NS}

REVIEW_PARTS = [
    "word/document.xml",
    "word/footnotes.xml",
]


def qn(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def load_decisions(path: str) -> dict[str, str]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(key): str(value).strip().lower() for key, value in raw.items()}


def load_review_manifest(archive: ZipFile) -> dict[str, dict[str, str]]:
    root = ET.fromstring(archive.read("customXml/item1.xml"))
    manifest: dict[str, dict[str, str]] = {}
    for item in root.findall(".//rv:item", NS):
        review_ref = item.get("reviewRef", "")
        if not review_ref:
            continue
        manifest[review_ref] = {
            "decision_key": item.get("decisionKey", ""),
            "part": item.get("part", ""),
            "comment_id": item.get("commentId", ""),
        }
    return manifest


def load_comment_map(archive: ZipFile, manifest: dict[str, dict[str, str]]) -> dict[str, str]:
    root = ET.fromstring(archive.read("word/comments.xml"))
    comment_map: dict[str, str] = {}
    for comment in root.findall(".//w:comment", NS):
        comment_id = comment.get(qn(W_NS, "id"), "")
        first_para = comment.find("./w:p", NS)
        text = "".join(node.text or "" for node in first_para.iter(qn(W_NS, "t"))) if first_para is not None else ""
        match = re.search(r"Review Ref:\s*([A-Z0-9-]+)", text)
        if not comment_id or not match:
            continue
        manifest_item = manifest.get(match.group(1))
        decision_key = manifest_item.get("decision_key", "") if manifest_item else ""
        if decision_key:
            comment_map[comment_id] = decision_key
    return comment_map


def paragraph_decision(para: ET.Element, comment_map: dict[str, str], decisions: dict[str, str]) -> str | None:
    for ref in para.findall(".//w:commentReference", NS):
        comment_id = ref.get(qn(W_NS, "id"), "")
        decision_key = comment_map.get(comment_id)
        if decision_key:
            return decisions.get(decision_key)
    return None


def strip_comment_markers(node: ET.Element) -> None:
    for parent in list(node.iter()):
        for child in list(parent):
            if child.tag in {
                qn(W_NS, "commentRangeStart"),
                qn(W_NS, "commentRangeEnd"),
                qn(W_NS, "commentReference"),
            }:
                parent.remove(child)
                continue

            if child.tag == qn(W_NS, "r") and child.find(qn(W_NS, "commentReference")) is not None:
                parent.remove(child)


def clone_run_from_deleted(run: ET.Element) -> ET.Element:
    new_run = ET.Element(qn(W_NS, "r"))
    for child in list(run):
        if child.tag == qn(W_NS, "delText"):
            replacement = ET.Element(qn(W_NS, "t"))
            replacement.text = child.text
            for attr_key, attr_val in child.attrib.items():
                replacement.set(attr_key, attr_val)
            new_run.append(replacement)
        else:
            new_run.append(child)
    return new_run


def replace_node_with_children(parent: ET.Element, node: ET.Element, children: list[ET.Element]) -> None:
    index = list(parent).index(node)
    parent.remove(node)
    for offset, child in enumerate(children):
        parent.insert(index + offset, child)


def apply_decision_to_para(para: ET.Element, decision: str) -> None:
    for parent in list(para.iter()):
        for child in list(parent):
            if child.tag == qn(W_NS, "ins"):
                if decision == "accept":
                    replace_node_with_children(parent, child, list(child))
                else:
                    parent.remove(child)
            elif child.tag == qn(W_NS, "del"):
                if decision == "accept":
                    parent.remove(child)
                else:
                    lifted = [clone_run_from_deleted(run) for run in child.findall(qn(W_NS, "r"))]
                    replace_node_with_children(parent, child, lifted)


def process_story_part(xml_bytes: bytes, comment_map: dict[str, str], decisions: dict[str, str]) -> bytes:
    root = ET.fromstring(xml_bytes)
    for para in root.findall(".//w:p", NS):
        decision = paragraph_decision(para, comment_map, decisions)
        if decision in {"accept", "reject"}:
            apply_decision_to_para(para, decision)
        strip_comment_markers(para)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def remove_comments_relationship(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    for rel in list(root.findall(f"{{{PKG_REL_NS}}}Relationship")):
        if rel.get("Type") == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments":
            root.remove(rel)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def remove_comments_content_type(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    for override in list(root.findall(f"{{{CONTENT_TYPES_NS}}}Override")):
        if override.get("PartName") == "/word/comments.xml":
            root.remove(override)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def remove_track_revisions(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    for node in list(root.findall(qn(W_NS, "trackRevisions"))):
        root.remove(node)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def resolve_review_manifest(xml_bytes: bytes, decisions: dict[str, str]) -> bytes:
    root = ET.fromstring(xml_bytes)
    for item in root.findall(".//rv:item", NS):
        decision_key = item.get("decisionKey", "")
        resolution = decisions.get(decision_key, "")
        if resolution:
            item.set("status", "resolved")
            item.set("resolution", resolution)
        elif "status" not in item.attrib:
            item.set("status", "resolved")
        if item.get("pending"):
            del item.attrib["pending"]
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    decisions = load_decisions(args.decisions)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(args.input) as source, ZipFile(output_path, "w", compression=ZIP_DEFLATED) as target:
        manifest = load_review_manifest(source)
        comment_map = load_comment_map(source, manifest)

        for info in source.infolist():
            if info.filename == "word/comments.xml":
                continue

            payload = source.read(info.filename)
            if info.filename in REVIEW_PARTS:
                payload = process_story_part(payload, comment_map, decisions)
            elif info.filename == "word/_rels/document.xml.rels":
                payload = remove_comments_relationship(payload)
            elif info.filename == "[Content_Types].xml":
                payload = remove_comments_content_type(payload)
            elif info.filename == "word/settings.xml":
                payload = remove_track_revisions(payload)
            elif info.filename == "customXml/item1.xml":
                payload = resolve_review_manifest(payload, decisions)

            target.writestr(info, payload)


if __name__ == "__main__":
    main()
