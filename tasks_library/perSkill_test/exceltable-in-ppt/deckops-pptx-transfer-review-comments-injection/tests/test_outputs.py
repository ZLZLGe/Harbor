import os
import unittest
import zipfile
from xml.etree import ElementTree as ET

RESULT_FILE = os.environ.get("RESULT_FILE", "/root/review-comments-injected.pptx")
INPUT_FILE = os.environ.get("INPUT_FILE", "/root/compliance-review-deck.pptx")

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {"a": A_NS, "p": P_NS}

EXPECTED_AUTHORS = {
    ("Iris Tan", "IT"): {
        "comments": {
            "Add the contractor monitoring exception.": ("ppt/slides/slide2.xml", "Policy Coverage"),
            "Quote the retention period from the policy appendix.": ("ppt/slides/slide3.xml", "Evidence Gaps"),
        }
    },
    ("Omar Ali", "OA"): {
        "comments": {
            "State who owns the remediation tracker.": ("ppt/slides/slide2.xml", "Open Issues"),
        }
    },
}


def read_zip_xml(zf, path):
    return ET.fromstring(zf.read(path))


def slide_shape_bounds(zf, slide_path):
    root = read_zip_xml(zf, slide_path)
    bounds = {}
    for shape in root.findall(".//p:sp", NS):
        tx_body = shape.find("./p:txBody", NS)
        xfrm = shape.find("./p:spPr/a:xfrm", NS)
        if tx_body is None or xfrm is None:
            continue
        paragraphs = []
        for para in tx_body.findall("./a:p", NS):
            text = "".join(node.text or "" for node in para.findall(".//a:t", NS)).strip()
            if text:
                paragraphs.append(text)
        if not paragraphs:
            continue
        off = xfrm.find("./a:off", NS)
        ext = xfrm.find("./a:ext", NS)
        bounds[paragraphs[0]] = {
            "paragraphs": paragraphs,
            "x": int(off.attrib["x"]),
            "y": int(off.attrib["y"]),
            "cx": int(ext.attrib["cx"]),
            "cy": int(ext.attrib["cy"]),
        }
    return bounds


def slide_text_snapshot(zf, slide_path):
    snapshot = {}
    for key, info in slide_shape_bounds(zf, slide_path).items():
        snapshot[key] = tuple(info["paragraphs"])
    return snapshot


def comment_target_for_slide(zf, slide_path):
    rels_path = slide_path.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
    rels_root = read_zip_xml(zf, rels_path)
    for rel in rels_root.findall("{%s}Relationship" % REL_NS):
        if rel.attrib.get("Type") == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments":
            target = rel.attrib["Target"]
            if target.startswith("../"):
                return "ppt/" + target[3:]
            return target
    return None


class ReviewCommentInjectionTests(unittest.TestCase):
    def test_output_exists(self):
        self.assertTrue(os.path.exists(RESULT_FILE), f"Missing output file: {RESULT_FILE}")

    def test_output_is_valid_zip(self):
        self.assertTrue(zipfile.is_zipfile(RESULT_FILE), "Output is not a valid PPTX file")

    def test_comment_author_metadata_exists(self):
        with zipfile.ZipFile(RESULT_FILE, "r") as zf:
            self.assertIn("ppt/commentAuthors.xml", zf.namelist())

    def test_author_entries_and_comment_mapping(self):
        with zipfile.ZipFile(RESULT_FILE, "r") as zf:
            author_root = read_zip_xml(zf, "ppt/commentAuthors.xml")
            authors = {}
            for author in author_root.findall(f"{{{P_NS}}}cmAuthor"):
                key = (author.attrib["name"], author.attrib["initials"])
                authors[int(author.attrib["id"])] = {
                    "key": key,
                    "last_idx": int(author.attrib["lastIdx"]),
                }

            self.assertEqual(set(info["key"] for info in authors.values()), set(EXPECTED_AUTHORS))

            seen_counts = {key: 0 for key in EXPECTED_AUTHORS}
            for slide_path in ["ppt/slides/slide2.xml", "ppt/slides/slide3.xml"]:
                comment_part = comment_target_for_slide(zf, slide_path)
                self.assertIsNotNone(comment_part, f"{slide_path} is missing a comments relationship")
                comment_root = read_zip_xml(zf, comment_part)
                for cm in comment_root.findall(f"{{{P_NS}}}cm"):
                    author = authors[int(cm.attrib["authorId"])]
                    comment_text = cm.find(f"{{{P_NS}}}text").text
                    self.assertIn(comment_text, EXPECTED_AUTHORS[author["key"]]["comments"])
                    seen_counts[author["key"]] += 1

            self.assertEqual(seen_counts[("Iris Tan", "IT")], 2)
            self.assertEqual(seen_counts[("Omar Ali", "OA")], 1)
            self.assertEqual(authors[next(k for k, v in authors.items() if v["key"] == ("Iris Tan", "IT"))]["last_idx"], 2)
            self.assertEqual(authors[next(k for k, v in authors.items() if v["key"] == ("Omar Ali", "OA"))]["last_idx"], 1)

    def test_comments_are_positioned_inside_target_textboxes(self):
        with zipfile.ZipFile(RESULT_FILE, "r") as zf:
            for expected_author, payload in EXPECTED_AUTHORS.items():
                for comment_text, (slide_path, label) in payload["comments"].items():
                    comment_part = comment_target_for_slide(zf, slide_path)
                    comment_root = read_zip_xml(zf, comment_part)
                    matching = None
                    for cm in comment_root.findall(f"{{{P_NS}}}cm"):
                        if cm.find(f"{{{P_NS}}}text").text == comment_text:
                            matching = cm
                            break
                    self.assertIsNotNone(matching, f"Missing expected comment '{comment_text}' on {slide_path}")

                    bounds = slide_shape_bounds(zf, slide_path)[label]
                    pos = matching.find(f"{{{P_NS}}}pos")
                    x = int(pos.attrib["x"])
                    y = int(pos.attrib["y"])

                    self.assertGreaterEqual(x, bounds["x"])
                    self.assertLessEqual(x, bounds["x"] + bounds["cx"])
                    self.assertGreaterEqual(y, bounds["y"])
                    self.assertLessEqual(y, bounds["y"] + bounds["cy"])

    def test_slide_text_is_unchanged(self):
        with zipfile.ZipFile(INPUT_FILE, "r") as in_zf, zipfile.ZipFile(RESULT_FILE, "r") as out_zf:
            for slide_path in ["ppt/slides/slide1.xml", "ppt/slides/slide2.xml", "ppt/slides/slide3.xml"]:
                self.assertEqual(slide_text_snapshot(in_zf, slide_path), slide_text_snapshot(out_zf, slide_path))

    def test_only_target_slides_gain_comments(self):
        with zipfile.ZipFile(RESULT_FILE, "r") as zf:
            self.assertIsNone(comment_target_for_slide(zf, "ppt/slides/slide1.xml"))
            self.assertIsNotNone(comment_target_for_slide(zf, "ppt/slides/slide2.xml"))
            self.assertIsNotNone(comment_target_for_slide(zf, "ppt/slides/slide3.xml"))


if __name__ == "__main__":
    unittest.main()
