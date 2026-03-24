#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

python3 - <<'PY'
import json
import math

import pdfplumber

DOCUMENT_PATH = "/root/compound_properties_table.dat"
OUTPUT_PATH = "/root/workspace/compound_neighbors.json"
COLUMNS = [
    "molecular_weight",
    "xlogp",
    "hbd",
    "hba",
    "tpsa",
]
QUERIES = [
    ("Acetaminophen", 3),
    ("Ibuprofen", 4),
]


def extract_rows(document_path):
    rows = []
    with pdfplumber.open(document_path) as handle:
        for page in handle.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("Compound Property Reference"):
                    continue
                if line.startswith("Page "):
                    continue
                if line.startswith("Compound |"):
                    continue
                if set(line) == {"-"}:
                    continue
                parts = [part.strip() for part in line.split("|")]
                if len(parts) != 6:
                    continue
                rows.append(
                    {
                        "compound": parts[0],
                        "molecular_weight": float(parts[1]),
                        "xlogp": float(parts[2]),
                        "hbd": float(parts[3]),
                        "hba": float(parts[4]),
                        "tpsa": float(parts[5]),
                    }
                )
    return rows


def normalize(rows):
    mins = {column: min(row[column] for row in rows) for column in COLUMNS}
    maxs = {column: max(row[column] for row in rows) for column in COLUMNS}
    normalized = {}
    for row in rows:
        normalized[row["compound"]] = {
            column: (row[column] - mins[column]) / (maxs[column] - mins[column])
            for column in COLUMNS
        }
    return normalized


def distance(left, right):
    return math.sqrt(sum((left[column] - right[column]) ** 2 for column in COLUMNS))


rows = extract_rows(DOCUMENT_PATH)
normalized = normalize(rows)

result = {
    "source_document": DOCUMENT_PATH,
    "distance_metric": "euclidean_on_minmax_normalized_columns",
    "normalized_columns": COLUMNS,
    "extracted_compound_count": len(rows),
    "queries": [],
}

for target, top_k in QUERIES:
    target_vector = normalized[target]
    neighbors = []
    for row in rows:
        name = row["compound"]
        if name == target:
            continue
        neighbors.append(
            {
                "compound": name,
                "distance": round(distance(target_vector, normalized[name]), 4),
            }
        )
    neighbors.sort(key=lambda item: (item["distance"], item["compound"]))
    result["queries"].append(
        {
            "target": target,
            "top_k": top_k,
            "neighbors": neighbors[:top_k],
        }
    )

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
PY
