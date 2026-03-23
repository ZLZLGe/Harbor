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
    "sparkling water": ["beverages", "ready to drink", "bottled water", "sparkling water"],
    "whole bean coffee": ["beverages", "hot drinks", "coffee", "whole bean coffee"],
    "tomato basil sauce": ["pantry", "sauces", "pasta sauce", "tomato basil sauce"],
    "tortilla chips": ["snacks", "salty snacks", "corn snacks", "tortilla chips"],
    "greek yogurt": ["refrigerated", "cultured dairy", "yogurt", "greek yogurt"],
}


def normalize(text: str) -> str:
    lowered = text.lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def classify(path: str) -> str:
    normalized = normalize(path)
    if "yogurt" in normalized:
        return "greek yogurt"
    if "coffee" in normalized:
        return "whole bean coffee"
    if "water" in normalized or "seltzer" in normalized:
        return "sparkling water"
    if "sauce" in normalized or "marinara" in normalized:
        return "tomato basil sauce"
    if "chip" in normalized:
        return "tortilla chips"
    raise ValueError(f"Unable to classify grocery path: {path}")


rows = []
with (DATA_DIR / "grocer_a.csv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        rows.append({"source": "grocer_a", "item_path": row["category_path"].strip()})

with (DATA_DIR / "grocer_b.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        payload = json.loads(line)
        rows.append({"source": "grocer_b", "item_path": payload["hierarchy"].strip()})

with (DATA_DIR / "grocer_c.tsv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        rows.append({"source": "grocer_c", "item_path": row["label_path"].strip()})

mapped_rows = []
for row in rows:
    levels = LEVELS[classify(row["item_path"])]
    mapped_rows.append(
        {
            "source": row["source"],
            "item_path": row["item_path"],
            "unified_department": levels[0],
            "unified_aisle": levels[1],
            "unified_shelf": levels[2],
            "unified_leaf": levels[3],
        }
    )

mapped_rows.sort(key=lambda item: (item["source"], item["item_path"]))

with (OUTPUT_DIR / "transfer1_grocery_rollup.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "source",
            "item_path",
            "unified_department",
            "unified_aisle",
            "unified_shelf",
            "unified_leaf",
        ],
    )
    writer.writeheader()
    writer.writerows(mapped_rows)

nodes = sorted(
    {
        (
            row["unified_department"],
            row["unified_aisle"],
            row["unified_shelf"],
            row["unified_leaf"],
        )
        for row in mapped_rows
    }
)
node_payload = [
    {
        "unified_department": department,
        "unified_aisle": aisle,
        "unified_shelf": shelf,
        "unified_leaf": leaf,
    }
    for department, aisle, shelf, leaf in nodes
]

with (OUTPUT_DIR / "transfer1_taxonomy_nodes.json").open("w", encoding="utf-8") as handle:
    json.dump(node_payload, handle, indent=2)
    handle.write("\n")
PY
