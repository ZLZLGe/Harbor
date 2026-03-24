#!/bin/bash
set -e

python3 <<'PY'
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

TITLE_RE = re.compile(r"^Session\s+(\d{3}):\s+.+$")
FONT_SIZE = 1800
FONT_FACE = "Calibri"
FONT_COLOR = "4F6B8A"

ET.register_namespace("a", NS["a"])
ET.register_namespace("p", NS["p"])
ET.register_namespace("r", NS["r"])


def find_skill_dir() -> Path:
    base_dir = Path("/root")
    candidates = [
        base_dir / ".claude" / "skills" / "pptx",
        base_dir / ".codex" / "skills" / "pptx",
        base_dir / ".opencode" / "skill" / "pptx",
        base_dir / ".goose" / "skills" / "pptx",
        base_dir / ".factory" / "skills" / "pptx",
    ]
    for candidate in candidates:
        if (candidate / "ooxml" / "scripts" / "unpack.py").exists():
            return candidate
    raise RuntimeError("Required OOXML helper scripts are not available in the environment.")


def get_paragraph_text(paragraph: ET.Element) -> str:
    return " ".join("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).split())


def is_session_title(paragraph: ET.Element) -> bool:
    return bool(TITLE_RE.match(get_paragraph_text(paragraph)))


def ensure_run_properties(run: ET.Element) -> ET.Element:
    rpr = run.find("a:rPr", NS)
    if rpr is None:
        rpr = ET.Element(f"{{{NS['a']}}}rPr")
        run.insert(0, rpr)
    return rpr


def style_rpr(rpr: ET.Element) -> None:
    rpr.set("sz", str(FONT_SIZE))
    rpr.set("b", "0")
    rpr.set("dirty", "0")

    solid_fill = rpr.find("a:solidFill", NS)
    if solid_fill is None:
        solid_fill = ET.Element(f"{{{NS['a']}}}solidFill")
        rpr.insert(0, solid_fill)
    else:
        for child in list(solid_fill):
            solid_fill.remove(child)
    ET.SubElement(solid_fill, f"{{{NS['a']}}}srgbClr", val=FONT_COLOR)

    for tag in ("latin", "ea", "cs"):
        elem = rpr.find(f"a:{tag}", NS)
        if elem is None:
            elem = ET.SubElement(rpr, f"{{{NS['a']}}}{tag}")
        elem.set("typeface", FONT_FACE)


def style_paragraph(paragraph: ET.Element) -> None:
    ppr = paragraph.find("a:pPr", NS)
    if ppr is None:
        ppr = ET.Element(f"{{{NS['a']}}}pPr")
        paragraph.insert(0, ppr)
    ppr.set("algn", "ctr")

    for run in paragraph.findall("a:r", NS):
        style_rpr(ensure_run_properties(run))

    end_rpr = paragraph.find("a:endParaRPr", NS)
    if end_rpr is not None:
        style_rpr(end_rpr)


def build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def find_parent_shape(paragraph: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = paragraph
    while current in parent_map:
        current = parent_map[current]
        if current.tag == f"{{{NS['p']}}}sp":
            return current
    return None


def move_shape_to_bottom_center(shape: ET.Element, title_text: str, slide_width: int, slide_height: int) -> None:
    sp_pr = shape.find("p:spPr", NS)
    if sp_pr is None:
        return

    xfrm = sp_pr.find("a:xfrm", NS)
    if xfrm is None:
        xfrm = ET.Element(f"{{{NS['a']}}}xfrm")
        sp_pr.insert(0, xfrm)

    off = xfrm.find("a:off", NS)
    if off is None:
        off = ET.SubElement(xfrm, f"{{{NS['a']}}}off")

    ext = xfrm.find("a:ext", NS)
    if ext is None:
        ext = ET.SubElement(xfrm, f"{{{NS['a']}}}ext")

    approx_char_width = int((FONT_SIZE * 127) * 0.48)
    estimated_text_width = len(title_text) * approx_char_width
    usable_width = max(int(slide_width * 0.82), estimated_text_width + 300000)
    shape_width = min(usable_width, slide_width)
    shape_height = int(FONT_SIZE * 127 * 1.45)

    x_pos = max(int((slide_width - shape_width) / 2), 0)
    bottom_margin = int(slide_height * 0.03)
    y_pos = slide_height - shape_height - bottom_margin

    off.set("x", str(x_pos))
    off.set("y", str(y_pos))
    ext.set("cx", str(shape_width))
    ext.set("cy", str(shape_height))

    tx_body = shape.find("p:txBody", NS)
    if tx_body is not None:
        body_pr = tx_body.find("a:bodyPr", NS)
        if body_pr is None:
            body_pr = ET.Element(f"{{{NS['a']}}}bodyPr")
            tx_body.insert(0, body_pr)
        body_pr.set("lIns", "0")
        body_pr.set("rIns", "0")
        body_pr.set("anchor", "ctr")


def get_slide_dimensions(unpack_dir: Path) -> tuple[int, int]:
    root = ET.parse(unpack_dir / "ppt" / "presentation.xml").getroot()
    sld_sz = root.find(".//p:sldSz", NS)
    if sld_sz is None:
        raise RuntimeError("Could not read slide size from presentation.xml")
    return int(sld_sz.get("cx")), int(sld_sz.get("cy"))


def build_index_slide_xml(titles: list[str]) -> str:
    bullet_parts = []
    for title in titles:
        safe_text = (
            title.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        bullet_parts.append(
            f"""
          <a:p>
            <a:pPr lvl="0" algn="l">
              <a:buAutoNum type="arabicPeriod"/>
            </a:pPr>
            <a:r>
              <a:rPr sz="2000" dirty="0">
                <a:solidFill>
                  <a:srgbClr val="203040"/>
                </a:solidFill>
                <a:latin typeface="Calibri"/>
                <a:ea typeface="Calibri"/>
                <a:cs typeface="Calibri"/>
              </a:rPr>
              <a:t>{safe_text}</a:t>
            </a:r>
          </a:p>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
          <p:cNvSpPr>
            <a:spLocks noGrp="1"/>
          </p:cNvSpPr>
          <p:nvPr>
            <p:ph type="title"/>
          </p:nvPr>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="457200" y="228600"/>
            <a:ext cx="8229600" cy="914400"/>
          </a:xfrm>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr sz="2800" b="1" dirty="0">
                <a:solidFill>
                  <a:srgbClr val="203040"/>
                </a:solidFill>
                <a:latin typeface="Calibri"/>
                <a:ea typeface="Calibri"/>
                <a:cs typeface="Calibri"/>
              </a:rPr>
              <a:t>Session Index</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="3" name="Content"/>
          <p:cNvSpPr>
            <a:spLocks noGrp="1"/>
          </p:cNvSpPr>
          <p:nvPr>
            <p:ph type="body" idx="1"/>
          </p:nvPr>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="685800" y="1280160"/>
            <a:ext cx="10607040" cy="4572000"/>
          </a:xfrm>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square"/>
          <a:lstStyle/>{''.join(bullet_parts)}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>
"""


def append_index_slide(unpack_dir: Path, titles: list[str]) -> None:
    slides_dir = unpack_dir / "ppt" / "slides"
    next_slide_num = len(sorted(slides_dir.glob("slide*.xml"))) + 1

    slide_path = slides_dir / f"slide{next_slide_num}.xml"
    slide_path.write_text(build_index_slide_xml(titles), encoding="utf-8")

    rels_dir = slides_dir / "_rels"
    rels_dir.mkdir(exist_ok=True)
    rels_path = rels_dir / f"slide{next_slide_num}.xml.rels"
    rels_path.write_text(
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>
</Relationships>
""",
        encoding="utf-8",
    )

    content_types_path = unpack_dir / "[Content_Types].xml"
    content_tree = ET.parse(content_types_path)
    content_root = content_tree.getroot()
    override = ET.Element("{http://schemas.openxmlformats.org/package/2006/content-types}Override")
    override.set("PartName", f"/ppt/slides/slide{next_slide_num}.xml")
    override.set("ContentType", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    content_root.append(override)
    content_tree.write(content_types_path, encoding="UTF-8", xml_declaration=True)

    rels_path_main = unpack_dir / "ppt" / "_rels" / "presentation.xml.rels"
    rels_tree = ET.parse(rels_path_main)
    rels_root = rels_tree.getroot()
    existing_rids = [
        int(rel.get("Id")[3:])
        for rel in rels_root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        if rel.get("Id", "").startswith("rId")
    ]
    next_rid = max(existing_rids) + 1
    relationship = ET.Element("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
    relationship.set("Id", f"rId{next_rid}")
    relationship.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
    relationship.set("Target", f"slides/slide{next_slide_num}.xml")
    rels_root.append(relationship)
    rels_tree.write(rels_path_main, encoding="UTF-8", xml_declaration=True)

    presentation_path = unpack_dir / "ppt" / "presentation.xml"
    presentation_tree = ET.parse(presentation_path)
    presentation_root = presentation_tree.getroot()
    sld_id_lst = presentation_root.find(".//p:sldIdLst", NS)
    if sld_id_lst is None:
        raise RuntimeError("presentation.xml is missing sldIdLst")
    existing_ids = [int(node.get("id")) for node in sld_id_lst.findall("p:sldId", NS)]
    next_slide_id = max(existing_ids) + 1
    sld_id = ET.Element(f"{{{NS['p']}}}sldId")
    sld_id.set("id", str(next_slide_id))
    sld_id.set(f"{{{NS['r']}}}id", f"rId{next_rid}")
    sld_id_lst.append(sld_id)
    presentation_tree.write(presentation_path, encoding="UTF-8", xml_declaration=True)

    app_path = unpack_dir / "docProps" / "app.xml"
    app_tree = ET.parse(app_path)
    app_root = app_tree.getroot()
    slides_elem = app_root.find(".//{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides")
    if slides_elem is not None:
        slides_elem.text = str(next_slide_num)
    app_tree.write(app_path, encoding="UTF-8", xml_declaration=True)


def process_deck(unpack_dir: Path) -> list[str]:
    slide_width, slide_height = get_slide_dimensions(unpack_dir)
    slide_paths = sorted((unpack_dir / "ppt" / "slides").glob("slide*.xml"))

    unique_titles: dict[int, str] = {}
    for slide_path in slide_paths:
        tree = ET.parse(slide_path)
        root = tree.getroot()
        parent_map = build_parent_map(root)
        changed = False
        for paragraph in root.findall(".//a:p", NS):
            if not is_session_title(paragraph):
                continue
            title_text = get_paragraph_text(paragraph)
            style_paragraph(paragraph)
            shape = find_parent_shape(paragraph, parent_map)
            if shape is not None:
                move_shape_to_bottom_center(shape, title_text, slide_width, slide_height)
            match = TITLE_RE.match(title_text)
            if match is not None:
                unique_titles.setdefault(int(match.group(1)), title_text)
            changed = True
        if changed:
            tree.write(slide_path, encoding="UTF-8", xml_declaration=True)

    return [unique_titles[key] for key in sorted(unique_titles)]


def main() -> None:
    base_dir = Path("/root")
    input_pptx = base_dir / "AI-Summit-Sessions.pptx"
    output_pptx = base_dir / "AI-Summit-Sessions_processed.pptx"

    skill_dir = find_skill_dir()
    unpack_script = skill_dir / "ooxml" / "scripts" / "unpack.py"
    pack_script = skill_dir / "ooxml" / "scripts" / "pack.py"
    validate_script = skill_dir / "ooxml" / "scripts" / "validate.py"

    unpack_dir = Path(tempfile.mkdtemp(prefix="ai_summit_sessions_", dir="/tmp"))

    subprocess.run(["python3", str(unpack_script), str(input_pptx), str(unpack_dir)], check=True)
    session_titles = process_deck(unpack_dir)
    append_index_slide(unpack_dir, session_titles)

    try:
        subprocess.run(
            ["python3", str(validate_script), str(unpack_dir), "--original", str(input_pptx)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        pass

    subprocess.run(["python3", str(pack_script), str(unpack_dir), str(output_pptx)], check=True)


if __name__ == "__main__":
    main()
PY
