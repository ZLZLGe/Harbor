import os
import zipfile
from xml.etree import ElementTree as ET

INPUT_FILE = "/root/sales-overview-draft.pptx"
RESULT_FILE = "/root/results-table-revision.pptx"
SLIDE_XML = "ppt/slides/slide1.xml"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

EXPECTED_UPDATES = {
    ("North", "Q3"): "5.1",
    ("Online", "Q4"): "6.4",
    ("Grand Total", "Q4"): "18.2",
}
EXPECTED_FOOTER = "Last revised: 2026-03-10"


def load_slide(path):
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read(SLIDE_XML))


def shape_lines(shape):
    lines = []
    for paragraph in shape.findall(".//a:p", NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).strip()
        if text:
            lines.append(text)
    return lines


def extract_table(root):
    table = root.find(".//a:tbl", NS)
    assert table is not None, "Slide does not contain a native PowerPoint table"
    rows = []
    for tr in table.findall("a:tr", NS):
        row = []
        for tc in tr.findall("a:tc", NS):
            row.append("".join(node.text or "" for node in tc.findall(".//a:t", NS)).strip())
        rows.append(row)
    return rows


def table_to_dict(rows):
    headers = rows[0]
    mapped = {}
    for row in rows[1:]:
        row_label = row[0]
        for idx, value in enumerate(row[1:], start=1):
            mapped[(row_label, headers[idx])] = value
    return mapped


def extract_shape_snapshots(root):
    snapshots = []
    for shape in root.findall(".//p:sp", NS):
        c_nv_pr = shape.find("p:nvSpPr/p:cNvPr", NS)
        xfrm = shape.find("p:spPr/a:xfrm", NS)
        off = xfrm.find("a:off", NS)
        ext = xfrm.find("a:ext", NS)
        snapshots.append(
            {
                "id": c_nv_pr.attrib["id"],
                "name": c_nv_pr.attrib.get("name", ""),
                "kind": "shape",
                "text": shape_lines(shape),
                "x": off.attrib["x"],
                "y": off.attrib["y"],
                "cx": ext.attrib["cx"],
                "cy": ext.attrib["cy"],
            }
        )

    for frame in root.findall(".//p:graphicFrame", NS):
        c_nv_pr = frame.find("p:nvGraphicFramePr/p:cNvPr", NS)
        xfrm = frame.find("p:xfrm", NS)
        off = xfrm.find("a:off", NS)
        ext = xfrm.find("a:ext", NS)
        snapshots.append(
            {
                "id": c_nv_pr.attrib["id"],
                "name": c_nv_pr.attrib.get("name", ""),
                "kind": "graphicFrame",
                "text": [],
                "x": off.attrib["x"],
                "y": off.attrib["y"],
                "cx": ext.attrib["cx"],
                "cy": ext.attrib["cy"],
            }
        )

    return sorted(snapshots, key=lambda item: (item["kind"], int(item["id"])))


def footer_text(root):
    for shape in root.findall(".//p:sp", NS):
        lines = shape_lines(shape)
        if len(lines) == 1 and lines[0].startswith("Last revised:"):
            return lines[0]
    raise AssertionError("Footer text box was not found")


def memo_lines(root):
    for shape in root.findall(".//p:sp", NS):
        lines = shape_lines(shape)
        if lines and lines[0] == "Revision memo":
            return lines
    raise AssertionError("Revision memo text box was not found")


def test_output_exists_and_is_zip():
    assert os.path.exists(RESULT_FILE), "Output PPTX was not created"
    assert zipfile.is_zipfile(RESULT_FILE), "Output file is not a valid PPTX archive"


def test_native_table_cells_are_updated():
    rows = extract_table(load_slide(RESULT_FILE))
    table = table_to_dict(rows)
    for key, expected in EXPECTED_UPDATES.items():
        assert table[key] == expected, f"Cell {key} should be {expected}, got {table[key]}"


def test_only_requested_table_cells_change():
    input_table = table_to_dict(extract_table(load_slide(INPUT_FILE)))
    output_table = table_to_dict(extract_table(load_slide(RESULT_FILE)))

    changed = {key for key in input_table if input_table[key] != output_table[key]}
    assert changed == set(EXPECTED_UPDATES), f"Unexpected table edits detected: {changed}"


def test_footer_date_is_synced_from_memo():
    root = load_slide(RESULT_FILE)
    assert footer_text(root) == EXPECTED_FOOTER
    assert memo_lines(root)[-1] == EXPECTED_FOOTER


def test_other_text_boxes_remain_unchanged():
    input_root = load_slide(INPUT_FILE)
    output_root = load_slide(RESULT_FILE)

    input_shapes = {
        (item["kind"], item["id"]): item
        for item in extract_shape_snapshots(input_root)
    }
    output_shapes = {
        (item["kind"], item["id"]): item
        for item in extract_shape_snapshots(output_root)
    }

    assert input_shapes.keys() == output_shapes.keys(), "Slide object set changed unexpectedly"

    for key, input_item in input_shapes.items():
        output_item = output_shapes[key]
        assert (
            input_item["x"],
            input_item["y"],
            input_item["cx"],
            input_item["cy"],
        ) == (
            output_item["x"],
            output_item["y"],
            output_item["cx"],
            output_item["cy"],
        ), f"Object geometry changed for {input_item['name']}"

        if input_item["kind"] == "graphicFrame":
            continue

        if input_item["name"] == "Footer":
            assert output_item["text"] == [EXPECTED_FOOTER]
            continue

        assert input_item["text"] == output_item["text"], f"Text changed for {input_item['name']}"
