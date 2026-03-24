#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path


def read_pgm(path: Path):
    with path.open("r", encoding="ascii") as handle:
        tokens = []
        for line in handle:
            line = line.split("#", 1)[0].strip()
            if line:
                tokens.extend(line.split())

    assert tokens[0] == "P2", f"Unsupported PGM format in {path}"
    width = int(tokens[1])
    height = int(tokens[2])
    _max_value = int(tokens[3])
    pixels = list(map(int, tokens[4:]))
    assert len(pixels) == width * height, f"Invalid pixel count in {path}"
    return [pixels[i * width : (i + 1) * width] for i in range(height)]


def count_matches(image, template):
    image_h = len(image)
    image_w = len(image[0])
    template_h = len(template)
    template_w = len(template[0])
    count = 0

    for top in range(image_h - template_h + 1):
        for left in range(image_w - template_w + 1):
            matched = True
            for dy in range(template_h):
                if image[top + dy][left : left + template_w] != template[dy]:
                    matched = False
                    break
            if matched:
                count += 1
    return count


root = Path("/root")
pages = [
    ("page_001", root / "form_pages" / "page_001.pgm"),
    ("page_002", root / "form_pages" / "page_002.pgm"),
    ("page_003", root / "form_pages" / "page_003.pgm"),
    ("page_004", root / "form_pages" / "page_004.pgm"),
]
refs = {
    "paid_stamps": read_pgm(root / "markup_refs" / "paid_stamp.pgm"),
    "review_stamps": read_pgm(root / "markup_refs" / "review_stamp.pgm"),
    "warning_stickers": read_pgm(root / "markup_refs" / "warning_sticker.pgm"),
}

rows = []
totals = {"paid_stamps": 0, "review_stamps": 0, "warning_stickers": 0}

for page_id, page_path in pages:
    image = read_pgm(page_path)
    counts = {key: count_matches(image, template) for key, template in refs.items()}
    total_markups = sum(counts.values())
    rows.append(
        [
            page_id,
            str(page_path),
            str(counts["paid_stamps"]),
            str(counts["review_stamps"]),
            str(counts["warning_stickers"]),
            str(total_markups),
        ]
    )
    for key in totals:
        totals[key] += counts[key]

grand_total = sum(totals.values())
output = root / "form_markup_counts.tsv"
with output.open("w", encoding="utf-8", newline="") as handle:
    handle.write(
        "page_id\tpage_file\tpaid_stamps\treview_stamps\twarning_stickers\ttotal_markups\n"
    )
    for row in rows:
        handle.write("\t".join(row) + "\n")
    handle.write(
        "\t".join(
            [
                "TOTAL",
                "ALL_PAGES",
                str(totals["paid_stamps"]),
                str(totals["review_stamps"]),
                str(totals["warning_stickers"]),
                str(grand_total),
            ]
        )
        + "\n"
    )
PY
