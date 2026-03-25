#!/bin/bash
set -euo pipefail

python3 <<'PY'
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from lxml import etree

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
PACKAGE_NS = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
CREDIT_RE = re.compile(r"^(Photo by .+|Image credit: .+)$")


def normalize(text: str) -> str:
    return " ".join(text.split())


def paragraph_text(paragraph: etree._Element) -> str:
    return "".join(paragraph.xpath(".//a:t/text()", namespaces=NS))


def get_slide_dimensions(unpack_dir: Path) -> tuple[int, int]:
    root = etree.parse(str(unpack_dir / "ppt" / "presentation.xml")).getroot()
    size = root.find(".//p:sldSz", NS)
    if size is None:
        raise RuntimeError("presentation.xml is missing slide size information")
    return int(size.get("cx")), int(size.get("cy"))


def find_shape(node: etree._Element) -> etree._Element | None:
    current = node
    while current is not None:
        if current.tag == f"{{{NS['p']}}}sp":
            return current
        current = current.getparent()
    return None


def ensure_rpr(run: etree._Element) -> etree._Element:
    rpr = run.find("a:rPr", NS)
    if rpr is None:
        rpr = etree.Element(f"{{{NS['a']}}}rPr")
        run.insert(0, rpr)
    return rpr


def apply_credit_style(rpr: etree._Element) -> None:
    rpr.set("sz", "1200")
    rpr.set("i", "1")
    rpr.set("b", "0")
    solid_fill = rpr.find("a:solidFill", NS)
    if solid_fill is None:
        solid_fill = etree.Element(f"{{{NS['a']}}}solidFill")
        rpr.insert(0, solid_fill)
    for child in list(solid_fill):
        solid_fill.remove(child)
    etree.SubElement(solid_fill, f"{{{NS['a']}}}srgbClr").set("val", "4A4A4A")
    for key in ("latin", "ea", "cs"):
        node = rpr.find(f"a:{key}", NS)
        if node is None:
            node = etree.SubElement(rpr, f"{{{NS['a']}}}{key}")
        node.set("typeface", "Calibri")


def rewrite_credit_shape(shape: etree._Element, credit_text: str, slide_width: int, slide_height: int) -> None:
    tx_body = shape.find("p:txBody", NS)
    if tx_body is None:
        raise RuntimeError("Credit shape is missing txBody")

    body_pr = tx_body.find("a:bodyPr", NS)
    if body_pr is None:
        body_pr = etree.Element(f"{{{NS['a']}}}bodyPr")
        tx_body.insert(0, body_pr)
    body_pr.set("wrap", "none")
    body_pr.set("anchor", "b")

    paragraphs = tx_body.findall("a:p", NS)
    if not paragraphs:
        paragraph = etree.SubElement(tx_body, f"{{{NS['a']}}}p")
    else:
        paragraph = paragraphs[0]
        for extra in paragraphs[1:]:
            tx_body.remove(extra)

    for child in list(paragraph):
        paragraph.remove(child)

    ppr = etree.SubElement(paragraph, f"{{{NS['a']}}}pPr")
    ppr.set("algn", "r")

    run = etree.SubElement(paragraph, f"{{{NS['a']}}}r")
    rpr = etree.SubElement(run, f"{{{NS['a']}}}rPr")
    apply_credit_style(rpr)
    etree.SubElement(run, f"{{{NS['a']}}}t").text = credit_text

    end_rpr = etree.SubElement(paragraph, f"{{{NS['a']}}}endParaRPr")
    apply_credit_style(end_rpr)

    sp_pr = shape.find("p:spPr", NS)
    if sp_pr is None:
        raise RuntimeError("Credit shape is missing spPr")
    xfrm = sp_pr.find("a:xfrm", NS)
    if xfrm is None:
        xfrm = etree.Element(f"{{{NS['a']}}}xfrm")
        sp_pr.insert(0, xfrm)
    off = xfrm.find("a:off", NS)
    if off is None:
        off = etree.SubElement(xfrm, f"{{{NS['a']}}}off")
    ext = xfrm.find("a:ext", NS)
    if ext is None:
        ext = etree.SubElement(xfrm, f"{{{NS['a']}}}ext")

    font_height = 12 * 12700
    box_height = int(font_height * 1.45)
    box_width = int(slide_width * 0.34)
    margin_x = int(slide_width * 0.03)
    margin_y = int(slide_height * 0.03)
    off.set("x", str(slide_width - box_width - margin_x))
    off.set("y", str(slide_height - box_height - margin_y))
    ext.set("cx", str(box_width))
    ext.set("cy", str(box_height))


def create_summary_slide(unpack_dir: Path, credits: list[str]) -> None:
    slides_dir = unpack_dir / "ppt" / "slides"
    slide_numbers = sorted(
        int(path.stem.replace("slide", ""))
        for path in slides_dir.glob("slide*.xml")
        if path.stem.replace("slide", "").isdigit()
    )
    next_slide_num = slide_numbers[-1] + 1
    slide_path = slides_dir / f"slide{next_slide_num}.xml"

    escaped_items = []
    for credit in credits:
        escaped = (
            credit.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        escaped_items.append(
            f"""
          <a:p>
            <a:pPr lvl="0">
              <a:buAutoNum type="arabicPeriod"/>
            </a:pPr>
            <a:r>
              <a:rPr sz="1800" dirty="0">
                <a:solidFill><a:srgbClr val="1F1F1F"/></a:solidFill>
                <a:latin typeface="Calibri"/>
                <a:ea typeface="Calibri"/>
                <a:cs typeface="Calibri"/>
              </a:rPr>
              <a:t>{escaped}</a:t>
            </a:r>
            <a:endParaRPr sz="1800" dirty="0">
              <a:latin typeface="Calibri"/>
              <a:ea typeface="Calibri"/>
              <a:cs typeface="Calibri"/>
            </a:endParaRPr>
          </a:p>"""
        )

    slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
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
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="2" name="Title"/>
          <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
          <p:nvPr><p:ph type="title"/></p:nvPr>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="457200" y="274638"/>
            <a:ext cx="8229600" cy="1143000"/>
          </a:xfrm>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr sz="2800" dirty="0">
                <a:solidFill><a:srgbClr val="1F1F1F"/></a:solidFill>
                <a:latin typeface="Calibri"/>
                <a:ea typeface="Calibri"/>
                <a:cs typeface="Calibri"/>
              </a:rPr>
              <a:t>Image Credits</a:t>
            </a:r>
            <a:endParaRPr sz="2800" dirty="0">
              <a:latin typeface="Calibri"/>
              <a:ea typeface="Calibri"/>
              <a:cs typeface="Calibri"/>
            </a:endParaRPr>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="3" name="Content"/>
          <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
          <p:nvPr><p:ph type="body" idx="1"/></p:nvPr>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="685800" y="1371600"/>
            <a:ext cx="9836160" cy="4343400"/>
          </a:xfrm>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>{''.join(escaped_items)}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>"""
    slide_path.write_text(slide_xml, encoding="utf-8")

    rels_dir = slides_dir / "_rels"
    rels_dir.mkdir(exist_ok=True)
    (rels_dir / f"slide{next_slide_num}.xml.rels").write_text(
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>
</Relationships>""",
        encoding="utf-8",
    )

    content_types_path = unpack_dir / "[Content_Types].xml"
    ct_tree = etree.parse(str(content_types_path))
    ct_root = ct_tree.getroot()
    override = etree.Element(f"{{{PACKAGE_NS['ct']}}}Override")
    override.set("PartName", f"/ppt/slides/slide{next_slide_num}.xml")
    override.set("ContentType", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    ct_root.append(override)
    ct_tree.write(str(content_types_path), xml_declaration=True, encoding="UTF-8", standalone="yes")

    rels_path = unpack_dir / "ppt" / "_rels" / "presentation.xml.rels"
    rels_tree = etree.parse(str(rels_path))
    rels_root = rels_tree.getroot()
    rid_values = [
        int(rel.get("Id")[3:])
        for rel in rels_root.findall("rel:Relationship", REL_NS)
        if rel.get("Id", "").startswith("rId")
    ]
    next_rid = max(rid_values) + 1
    rel = etree.Element(f"{{{REL_NS['rel']}}}Relationship")
    rel.set("Id", f"rId{next_rid}")
    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
    rel.set("Target", f"slides/slide{next_slide_num}.xml")
    rels_root.append(rel)
    rels_tree.write(str(rels_path), xml_declaration=True, encoding="UTF-8", standalone="yes")

    presentation_path = unpack_dir / "ppt" / "presentation.xml"
    pres_tree = etree.parse(str(presentation_path))
    pres_root = pres_tree.getroot()
    sld_id_list = pres_root.find(".//p:sldIdLst", NS)
    if sld_id_list is None:
        raise RuntimeError("presentation.xml is missing sldIdLst")
    existing_slide_ids = [int(node.get("id")) for node in sld_id_list.findall("p:sldId", NS)]
    next_slide_id = max(existing_slide_ids) + 1
    sld_id = etree.Element(f"{{{NS['p']}}}sldId")
    sld_id.set("id", str(next_slide_id))
    sld_id.set(f"{{{NS['r']}}}id", f"rId{next_rid}")
    sld_id_list.append(sld_id)
    pres_tree.write(str(presentation_path), xml_declaration=True, encoding="UTF-8", standalone="yes")

    app_path = unpack_dir / "docProps" / "app.xml"
    if app_path.exists():
        app_tree = etree.parse(str(app_path))
        app_root = app_tree.getroot()
        slides_elem = app_root.find(".//{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides")
        if slides_elem is not None:
            slides_elem.text = str(next_slide_num)
        app_tree.write(str(app_path), xml_declaration=True, encoding="UTF-8", standalone="yes")


def process_deck(unpack_dir: Path) -> list[str]:
    slide_width, slide_height = get_slide_dimensions(unpack_dir)
    slides_dir = unpack_dir / "ppt" / "slides"
    slide_files = sorted(
        (path for path in slides_dir.glob("slide*.xml") if path.stem.replace("slide", "").isdigit()),
        key=lambda path: int(path.stem.replace("slide", "")),
    )
    credits: list[str] = []
    seen: set[str] = set()

    parser = etree.XMLParser(remove_blank_text=False)
    for slide_path in slide_files:
        tree = etree.parse(str(slide_path), parser)
        root = tree.getroot()
        changed = False
        for paragraph in root.xpath(".//a:p", namespaces=NS):
            text = normalize(paragraph_text(paragraph))
            if not CREDIT_RE.fullmatch(text):
                continue
            shape = find_shape(paragraph)
            if shape is None:
                continue
            rewrite_credit_shape(shape, text, slide_width, slide_height)
            changed = True
            if text not in seen:
                seen.add(text)
                credits.append(text)
        if changed:
            tree.write(str(slide_path), xml_declaration=True, encoding="UTF-8", standalone="yes")
    return credits


def main() -> None:
    base = Path("/root")
    input_ppt = base / "Case-Study-Credits.pptx"
    output_ppt = base / "Case-Study-Credits-cleaned.pptx"
    skill_root = base / ".codex" / "skills" / "pptx" / "ooxml" / "scripts"
    unpack_script = skill_root / "unpack.py"
    pack_script = skill_root / "pack.py"
    validate_script = skill_root / "validate.py"
    unpack_dir = Path(tempfile.mkdtemp(prefix="case_study_credits_"))

    subprocess.run(["python3", str(unpack_script), str(input_ppt), str(unpack_dir)], check=True)
    credits = process_deck(unpack_dir)
    create_summary_slide(unpack_dir, credits)

    try:
        subprocess.run(
            ["python3", str(validate_script), str(unpack_dir), "--original", str(input_ppt)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        pass

    subprocess.run(["python3", str(pack_script), str(unpack_dir), str(output_ppt), "--force"], check=True)


if __name__ == "__main__":
    main()
PY
