from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from zipfile import ZipFile
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REVIEW_NS = "urn:northharbor:review-manifest"
NS = {"w": W_NS, "rv": REVIEW_NS}

REVIEW_PARTS = [
    "word/document.xml",
    "word/footnotes.xml",
]


@dataclass
class ParagraphRecord:
    part: str
    review_ref: str
    decision_key: str
    comment_id: str
    rendered_text: str


def render_revision_text(paragraph: ET.Element) -> str:
    chunks: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{{{W_NS}}}t":
            chunks.append(node.text or "")
        elif node.tag == f"{{{W_NS}}}delText":
            chunks.append(node.text or "")
    return "".join(chunks).strip()


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


def load_comment_map(archive: ZipFile, manifest: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    root = ET.fromstring(archive.read("word/comments.xml"))
    comment_map: dict[str, dict[str, str]] = {}
    for comment in root.findall(".//w:comment", NS):
        comment_id = comment.get(f"{{{W_NS}}}id", "")
        first_para = comment.find("./w:p", NS)
        text = "".join(node.text or "" for node in first_para.iter(f"{{{W_NS}}}t")) if first_para is not None else ""
        match = re.search(r"Review Ref:\s*([A-Z0-9-]+)", text)
        if not comment_id or not match:
            continue
        review_ref = match.group(1)
        manifest_item = manifest.get(review_ref, {})
        comment_map[comment_id] = {
            "review_ref": review_ref,
            "decision_key": manifest_item.get("decision_key", "UNKNOWN"),
        }
    return comment_map


def collect_records(docx_path: str) -> list[ParagraphRecord]:
    records: list[ParagraphRecord] = []
    with ZipFile(docx_path) as archive:
        manifest = load_review_manifest(archive)
        comment_map = load_comment_map(archive, manifest)

        for part in REVIEW_PARTS:
            if part not in archive.namelist():
                continue
            root = ET.fromstring(archive.read(part))
            for para in root.findall(".//w:p", NS):
                comment_refs = para.findall(".//w:commentReference", NS)
                if not comment_refs:
                    continue
                comment_id = comment_refs[0].get(f"{{{W_NS}}}id", "")
                mapped = comment_map.get(comment_id, {})
                records.append(
                    ParagraphRecord(
                        part=part,
                        review_ref=mapped.get("review_ref", "UNKNOWN"),
                        decision_key=mapped.get("decision_key", "UNKNOWN"),
                        comment_id=comment_id or "UNKNOWN",
                        rendered_text=render_revision_text(para),
                    )
                )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx")
    args = parser.parse_args()

    records = collect_records(args.docx)
    for record in records:
        print(
            f"[{record.part}] comment_id={record.comment_id} "
            f"review_ref={record.review_ref} decision_key={record.decision_key}"
        )
        print(record.rendered_text)


if __name__ == "__main__":
    main()
