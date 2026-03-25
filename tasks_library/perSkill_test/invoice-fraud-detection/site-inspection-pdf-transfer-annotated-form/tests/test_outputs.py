from pathlib import Path

from pypdf import PdfReader


INPUT_PATH = Path("/root/inspection_form.pdf")
OUTPUT_PATH = Path("/root/annotated_inspection_form.pdf")

EXPECTED_TEXT = {
    1: [
        {"text": "East Wharf Pump House", "region": [118, 642, 334, 672]},
        {"text": "2026-03-17", "region": [452, 642, 552, 672]},
        {"text": "Liang Chen", "region": [108, 602, 264, 632]},
        {"text": "PT-8841", "region": [364, 602, 504, 632]},
        {"text": "PS-14B", "region": [148, 402, 284, 432]},
        {"text": "118", "region": [404, 402, 506, 432]},
    ],
    2: [
        {"text": "Replace torn hose tag; tighten west rail bolt.", "region": [60, 548, 552, 600]},
    ],
}

EXPECTED_MARKS = {
    1: [
        {"text": "X", "region": [224, 562, 246, 584]},
        {"text": "X", "region": [548, 562, 570, 584]},
        {"text": "X", "region": [223, 522, 245, 544]},
        {"text": "X", "region": [189, 482, 211, 504]},
        {"text": "X", "region": [541, 482, 563, 504]},
        {"text": "X", "region": [175, 374, 197, 396]},
        {"text": "X", "region": [533, 374, 555, 396]},
    ],
    2: [
        {"text": "X", "region": [185, 660, 207, 682]},
    ],
}

UNSELECTED_MARK_REGIONS = {
    1: [
        [134, 562, 156, 584],
        [397, 562, 419, 584],
        [473, 562, 495, 584],
        [288, 522, 310, 544],
        [255, 482, 277, 504],
        [475, 482, 497, 504],
        [241, 374, 263, 396],
        [467, 374, 489, 396],
    ],
    2: [
        [251, 660, 273, 682],
    ],
}

EXPECTED_ADDITIONS = {
    page_number: EXPECTED_TEXT.get(page_number, []) + EXPECTED_MARKS.get(page_number, [])
    for page_number in {1, 2}
}


def normalize_text(value: str) -> str:
    return " ".join(str(value).split())


def read_visible_items(reader: PdfReader):
    items = {1: [], 2: []}
    for page_number, page in enumerate(reader.pages, start=1):
        for annot_ref in page.get("/Annots", []) or []:
            annot = annot_ref.get_object()
            text = normalize_text(annot.get("/Contents"))
            if not text:
                continue
            rect = [float(value) for value in annot["/Rect"]]
            items.setdefault(page_number, []).append(
                {
                    "kind": "annotation",
                    "text": text,
                    "rect": rect,
                    "point": None,
                }
            )

        def visitor(text, _cm, tm, _font_dict, _font_size):
            cleaned = normalize_text(text)
            if not cleaned:
                return
            items.setdefault(page_number, []).append(
                {
                    "kind": "text",
                    "text": cleaned,
                    "rect": None,
                    "point": [float(tm[4]), float(tm[5])],
                }
            )

        page.extract_text(visitor_text=visitor)
    return items


def rect_within(rect, region, tolerance=4):
    return (
        rect[0] >= region[0] - tolerance
        and rect[1] >= region[1] - tolerance
        and rect[2] <= region[2] + tolerance
        and rect[3] <= region[3] + tolerance
    )


def point_within(point, region, tolerance=14):
    return (
        region[0] - tolerance <= point[0] <= region[2] + tolerance
        and region[1] - tolerance <= point[1] <= region[3] + tolerance
    )


def item_within(item, region):
    if item["rect"] is not None:
        return rect_within(item["rect"], region)
    if item["point"] is not None:
        return point_within(item["point"], region)
    return False


def same_item(left, right):
    if left["kind"] != right["kind"] or left["text"] != right["text"]:
        return False
    if left["rect"] is not None and right["rect"] is not None:
        return all(abs(a - b) <= 2 for a, b in zip(left["rect"], right["rect"]))
    if left["point"] is not None and right["point"] is not None:
        return abs(left["point"][0] - right["point"][0]) <= 2 and abs(left["point"][1] - right["point"][1]) <= 2
    return False


def subtract_items(output_items, input_items):
    matched_input_indexes = set()
    additions = []
    for output_item in output_items:
        match_index = None
        for index, input_item in enumerate(input_items):
            if index in matched_input_indexes:
                continue
            if same_item(output_item, input_item):
                match_index = index
                break
        if match_index is None:
            additions.append(output_item)
        else:
            matched_input_indexes.add(match_index)
    return additions


def collapse_annotation_text_echoes(items):
    annotations = [item for item in items if item["kind"] == "annotation"]
    normalized_items = list(annotations)

    for text_item in [item for item in items if item["kind"] == "text"]:
        if any(
            text_item["text"] == annotation["text"] and item_within(text_item, annotation["rect"])
            for annotation in annotations
        ):
            continue
        normalized_items.append(text_item)

    return normalized_items


def get_added_visible_items():
    input_reader = PdfReader(str(INPUT_PATH))
    output_reader = PdfReader(str(OUTPUT_PATH))

    input_items = read_visible_items(input_reader)
    output_items = read_visible_items(output_reader)

    added_items = {}
    for page_number in range(1, len(output_reader.pages) + 1):
        page_additions = subtract_items(output_items.get(page_number, []), input_items.get(page_number, []))
        added_items[page_number] = collapse_annotation_text_echoes(page_additions)
    return added_items


def expected_matches(page_number, item):
    return [
        expected
        for expected in EXPECTED_ADDITIONS.get(page_number, [])
        if item["text"] == expected["text"] and item_within(item, expected["region"])
    ]


def test_output_exists():
    assert OUTPUT_PATH.exists(), "missing /root/annotated_inspection_form.pdf"


def test_page_structure_is_preserved():
    input_reader = PdfReader(str(INPUT_PATH))
    output_reader = PdfReader(str(OUTPUT_PATH))

    assert len(input_reader.pages) == 2
    assert len(output_reader.pages) == len(input_reader.pages)

    for input_page, output_page in zip(input_reader.pages, output_reader.pages):
        assert list(input_page.mediabox) == list(output_page.mediabox)


def test_expected_additions_are_complete_and_unique():
    added_items = get_added_visible_items()

    for page_number, expected_items in EXPECTED_ADDITIONS.items():
        page_items = added_items.get(page_number, [])
        for expected in expected_items:
            matches = [
                item
                for item in page_items
                if item["text"] == expected["text"] and item_within(item, expected["region"])
            ]
            assert len(matches) == 1, (
                f"expected exactly one added visible item on page {page_number} "
                f"for {expected['text']} within {expected['region']}, found {len(matches)}"
            )


def test_only_expected_content_was_added():
    added_items = get_added_visible_items()

    for page_number, page_items in added_items.items():
        for item in page_items:
            assert expected_matches(page_number, item), (
                f"unexpected added visible item on page {page_number}: "
                f"{item['text']} at rect={item['rect']} point={item['point']}"
            )


def test_unselected_boxes_remain_blank():
    added_items = get_added_visible_items()

    for page_number, regions in UNSELECTED_MARK_REGIONS.items():
        page_items = added_items.get(page_number, [])
        for region in regions:
            assert not any(
                item["text"] == "X" and item_within(item, region)
                for item in page_items
            ), f"unexpected X mark on page {page_number} within {region}"
