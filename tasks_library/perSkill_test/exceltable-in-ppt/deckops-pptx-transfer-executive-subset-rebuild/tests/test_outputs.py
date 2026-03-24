import os
import unittest
import zipfile
from xml.etree import ElementTree as ET

RESULT_FILE = os.environ.get("RESULT_FILE", "/root/executive-subset-deck.pptx")
INPUT_FILE = os.environ.get("INPUT_FILE", "/root/enterprise-program-review.pptx")

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

EXPECTED_SOURCE_SLIDES = [4, 2, 5, 2]


def ordered_slide_parts(pptx_path):
    with zipfile.ZipFile(pptx_path, "r") as zf:
        pres_root = ET.fromstring(zf.read("ppt/presentation.xml"))
        rels_root = ET.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels_root.findall(f"{{{REL_NS}}}Relationship")
        }
        ordered = []
        for slide in pres_root.find(f"{{{P_NS}}}sldIdLst"):
            rel_id = slide.attrib[f"{{{R_NS}}}id"]
            target = rel_map[rel_id]
            if target.startswith("../"):
                ordered.append("ppt/" + target[3:])
            else:
                ordered.append("ppt/" + target if not target.startswith("ppt/") else target)
        return ordered


def slide_snapshot(zf, slide_path):
    root = ET.fromstring(zf.read(slide_path))
    snapshot = []
    for shape in root.findall(f".//{{{P_NS}}}sp"):
        paragraphs = []
        for para in shape.findall(f".//{{{A_NS}}}p"):
            text = "".join(node.text or "" for node in para.findall(f".//{{{A_NS}}}t")).strip()
            if text:
                paragraphs.append(text)
        if paragraphs:
            snapshot.append(tuple(paragraphs))
    return tuple(snapshot)


def slide_layout_target(zf, slide_path):
    rels_path = slide_path.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
    rels_root = ET.fromstring(zf.read(rels_path))
    for rel in rels_root.findall(f"{{{REL_NS}}}Relationship"):
        if rel.attrib.get("Type") == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout":
            return rel.attrib["Target"]
    return None


class ExecutiveSubsetDeckTests(unittest.TestCase):
    def test_output_exists(self):
        self.assertTrue(os.path.exists(RESULT_FILE), f"Missing output file: {RESULT_FILE}")

    def test_output_is_valid_pptx(self):
        self.assertTrue(zipfile.is_zipfile(RESULT_FILE), "Output is not a valid PPTX file")

    def test_output_has_expected_slide_count(self):
        self.assertEqual(len(ordered_slide_parts(RESULT_FILE)), len(EXPECTED_SOURCE_SLIDES))

    def test_slide_order_matches_cover_sequence(self):
        with zipfile.ZipFile(INPUT_FILE, "r") as in_zf, zipfile.ZipFile(RESULT_FILE, "r") as out_zf:
            output_parts = ordered_slide_parts(RESULT_FILE)
            self.assertEqual(len(output_parts), len(EXPECTED_SOURCE_SLIDES))
            for output_part, source_slide_number in zip(output_parts, EXPECTED_SOURCE_SLIDES):
                source_part = f"ppt/slides/slide{source_slide_number}.xml"
                self.assertEqual(
                    slide_snapshot(out_zf, output_part),
                    slide_snapshot(in_zf, source_part),
                    f"{output_part} does not match source slide {source_slide_number}",
                )

    def test_cover_slide_is_not_present(self):
        with zipfile.ZipFile(INPUT_FILE, "r") as in_zf, zipfile.ZipFile(RESULT_FILE, "r") as out_zf:
            cover_snapshot = slide_snapshot(in_zf, "ppt/slides/slide1.xml")
            for output_part in ordered_slide_parts(RESULT_FILE):
                self.assertNotEqual(slide_snapshot(out_zf, output_part), cover_snapshot)

    def test_repeated_slide_is_duplicated(self):
        with zipfile.ZipFile(RESULT_FILE, "r") as out_zf:
            output_parts = ordered_slide_parts(RESULT_FILE)
            self.assertEqual(
                slide_snapshot(out_zf, output_parts[1]),
                slide_snapshot(out_zf, output_parts[3]),
            )

    def test_slide_layouts_stay_aligned_with_source(self):
        with zipfile.ZipFile(INPUT_FILE, "r") as in_zf, zipfile.ZipFile(RESULT_FILE, "r") as out_zf:
            output_parts = ordered_slide_parts(RESULT_FILE)
            for output_part, source_slide_number in zip(output_parts, EXPECTED_SOURCE_SLIDES):
                source_part = f"ppt/slides/slide{source_slide_number}.xml"
                self.assertEqual(
                    slide_layout_target(out_zf, output_part),
                    slide_layout_target(in_zf, source_part),
                )


if __name__ == "__main__":
    unittest.main()
