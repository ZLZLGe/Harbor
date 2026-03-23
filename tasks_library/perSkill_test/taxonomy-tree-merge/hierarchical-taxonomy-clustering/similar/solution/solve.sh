#!/bin/bash
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-/root/output}"
mkdir -p "$OUTPUT_DIR"

python3 - <<'PY'
import csv
import json
import os
import re
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))

LEVELS = {
    "stove": ["outdoor gear", "camping", "cook setup", "portable heat", "stove"],
    "lantern": ["outdoor gear", "camping", "camp lighting", "area lighting", "lantern"],
    "tent": ["outdoor gear", "camping", "sleep shelter", "tent shelter", "tent"],
    "chair": ["outdoor gear", "camping", "site comfort", "camp seating", "chair"],
    "cooler": ["outdoor gear", "camping", "food storage", "cold storage", "cooler"],
    "sleeping bag": ["outdoor gear", "camping", "sleep shelter", "sleep insulation", "sleeping bag"],
}


def normalize(text: str) -> str:
    lowered = text.lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def classify(path: str) -> str:
    normalized = normalize(path)
    if "sleeping bag" in normalized:
        return "sleeping bag"
    if "cooler" in normalized or "ice chest" in normalized:
        return "cooler"
    if "lantern" in normalized:
        return "lantern"
    if "stove" in normalized:
        return "stove"
    if "chair" in normalized:
        return "chair"
    if "tent" in normalized:
        return "tent"
    raise ValueError(f"Unable to classify category path: {path}")


rows = []

with (DATA_DIR / "alpha_market.csv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        rows.append({"source": "alpha", "category_path": row["category_path"].strip()})

with (DATA_DIR / "bravo_market.csv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        rows.append({"source": "bravo", "category_path": row["vendor_path"].strip()})

with (DATA_DIR / "charlie_market.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        payload = json.loads(line)
        rows.append({"source": "charlie", "category_path": payload["path"].strip()})

mapped_rows = []
for row in rows:
    unified_levels = LEVELS[classify(row["category_path"])]
    mapped_rows.append(
        {
            "source": row["source"],
            "category_path": row["category_path"],
            "unified_level_1": unified_levels[0],
            "unified_level_2": unified_levels[1],
            "unified_level_3": unified_levels[2],
            "unified_level_4": unified_levels[3],
            "unified_level_5": unified_levels[4],
        }
    )

mapped_rows.sort(key=lambda item: (item["source"], item["category_path"]))

full_path = OUTPUT_DIR / "similar_outdoor_taxonomy_full.csv"
with full_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "source",
            "category_path",
            "unified_level_1",
            "unified_level_2",
            "unified_level_3",
            "unified_level_4",
            "unified_level_5",
        ],
    )
    writer.writeheader()
    writer.writerows(mapped_rows)

hierarchy_rows = sorted(
    {
        (
            row["unified_level_1"],
            row["unified_level_2"],
            row["unified_level_3"],
            row["unified_level_4"],
            row["unified_level_5"],
        )
        for row in mapped_rows
    }
)

hierarchy_path = OUTPUT_DIR / "similar_outdoor_taxonomy_hierarchy.csv"
with hierarchy_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(
        [
            "unified_level_1",
            "unified_level_2",
            "unified_level_3",
            "unified_level_4",
            "unified_level_5",
        ]
    )
    writer.writerows(hierarchy_rows)
PY
