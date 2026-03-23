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
    "drawer-dividers": ["drawer organization", "compartment tools", "drawer dividers"],
    "storage-bins": ["general storage", "container storage", "storage bins"],
    "over-door-hooks": ["entryway storage", "hanging access", "over door hooks"],
    "shoe-racks": ["closet storage", "footwear storage", "shoe racks"],
    "laundry-hampers": ["laundry organization", "hamper storage", "laundry hampers"],
}


def normalize(text: str) -> str:
    lowered = text.lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def classify(path: str) -> str:
    normalized = normalize(path)
    if "drawer" in normalized and ("divider" in normalized or "separator" in normalized):
        return "drawer-dividers"
    if "hook" in normalized:
        return "over-door-hooks"
    if "shoe" in normalized and ("rack" in normalized or "shel" in normalized):
        return "shoe-racks"
    if "hamper" in normalized or ("laundry" in normalized and "basket" in normalized):
        return "laundry-hampers"
    if "bin" in normalized or "tote" in normalized or "container" in normalized:
        return "storage-bins"
    raise ValueError(f"Unable to classify routing path: {path}")


rows = []
with (DATA_DIR / "planner_a.csv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        rows.append({"source": "planner_a", "source_path": row["category_path"].strip()})

with (DATA_DIR / "planner_b.txt").open(encoding="utf-8") as handle:
    for line in handle:
        rows.append({"source": "planner_b", "source_path": line.strip()})

with (DATA_DIR / "planner_c.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        payload = json.loads(line)
        rows.append({"source": "planner_c", "source_path": payload["browse_path"].strip()})

route_rows = []
for row in rows:
    slug = classify(row["source_path"])
    unified_top, unified_mid, unified_leaf = LEVELS[slug]
    route_rows.append(
        {
            "source": row["source"],
            "source_path": row["source_path"],
            "unified_top": unified_top,
            "unified_mid": unified_mid,
            "unified_leaf": unified_leaf,
            "route_slug": slug,
        }
    )

route_rows.sort(key=lambda item: (item["source"], item["source_path"]))

with (OUTPUT_DIR / "transfer3_search_routes.tsv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "source",
            "source_path",
            "unified_top",
            "unified_mid",
            "unified_leaf",
            "route_slug",
        ],
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(route_rows)

catalog_rows = sorted(
    {
        (
            row["route_slug"],
            row["unified_top"],
            row["unified_mid"],
            row["unified_leaf"],
        )
        for row in route_rows
    }
)

catalog_lines = ["# Route Catalog", ""]
for slug, unified_top, unified_mid, unified_leaf in catalog_rows:
    catalog_lines.extend(
        [
            f"## {slug}",
            f"- unified_top: {unified_top}",
            f"- unified_mid: {unified_mid}",
            f"- unified_leaf: {unified_leaf}",
            "",
        ]
    )

(OUTPUT_DIR / "transfer3_route_catalog.md").write_text("\n".join(catalog_lines).rstrip() + "\n", encoding="utf-8")
PY
