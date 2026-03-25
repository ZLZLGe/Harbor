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
    "wet cat food": ["nutrition", "cat food", "wet cat food"],
    "training treats": ["nutrition", "dog treats", "training treats"],
    "litter mats": ["habitat", "litter care", "litter mats"],
    "bird toys": ["enrichment", "bird play", "bird toys"],
    "aquarium filters": ["aquatics", "filtration", "aquarium filters"],
}


def normalize(text: str) -> str:
    lowered = text.lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def classify(path: str) -> str:
    normalized = normalize(path)
    if "filter" in normalized or "filtration" in normalized:
        return "aquarium filters"
    if "bird" in normalized and ("toy" in normalized or "perch" in normalized):
        return "bird toys"
    if "litter" in normalized and "mat" in normalized:
        return "litter mats"
    if "treat" in normalized or "snack" in normalized:
        return "training treats"
    if ("cat" in normalized or "cats" in normalized) and ("food" in normalized or "meal" in normalized):
        return "wet cat food"
    raise ValueError(f"Unable to classify pet path: {path}")


rows = []
with (DATA_DIR / "supplier_one.csv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        rows.append({"source": "supplier_one", "category_path": row["category_path"].strip()})

for payload in json.loads((DATA_DIR / "supplier_two.json").read_text(encoding="utf-8")):
    rows.append({"source": "supplier_two", "category_path": payload["path"].strip()})

with (DATA_DIR / "supplier_three.txt").open(encoding="utf-8") as handle:
    for line in handle:
        source, path = line.strip().split("|", 1)
        rows.append({"source": "supplier_three", "category_path": path.strip()})

assignments = []
for row in rows:
    group, family, cluster = LEVELS[classify(row["category_path"])]
    assignments.append(
        {
            "source": row["source"],
            "category_path": row["category_path"],
            "unified_group": group,
            "unified_family": family,
            "unified_cluster": cluster,
        }
    )

assignments.sort(key=lambda item: (item["source"], item["category_path"]))

with (OUTPUT_DIR / "transfer2_bundle_assignments.json").open("w", encoding="utf-8") as handle:
    json.dump(assignments, handle, indent=2)
    handle.write("\n")

summary_counts = {}
summary_sources = {}
for row in assignments:
    key = (row["unified_group"], row["unified_family"], row["unified_cluster"])
    summary_counts[key] = summary_counts.get(key, 0) + 1
    summary_sources.setdefault(key, set()).add(row["source"])

summary_rows = []
for group, family, cluster in sorted(summary_counts):
    summary_rows.append(
        {
            "unified_group": group,
            "unified_family": family,
            "unified_cluster": cluster,
            "source_count": str(len(summary_sources[(group, family, cluster)])),
            "record_count": str(summary_counts[(group, family, cluster)]),
        }
    )

with (OUTPUT_DIR / "transfer2_cluster_summary.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "unified_group",
            "unified_family",
            "unified_cluster",
            "source_count",
            "record_count",
        ],
    )
    writer.writeheader()
    writer.writerows(summary_rows)
PY
