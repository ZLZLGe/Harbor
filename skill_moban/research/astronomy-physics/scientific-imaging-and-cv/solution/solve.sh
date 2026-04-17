#!/bin/bash
set -e

python3 - <<'PY'
import csv
import json
import os
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "image_metrics.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "image_report.json"
output_dir.mkdir(parents=True, exist_ok=True)

records = []
with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        bright_pixels = float(row["bright_pixels"])
        total_pixels = float(row["total_pixels"])
        edge_score = float(row["edge_score"])
        normalized = round(bright_pixels / total_pixels, 4)
        quality_tag = "sharp" if edge_score >= 0.70 else "soft"
        records.append(
            {
                "image_id": row["image_id"],
                "normalized_brightness": normalized,
                "quality_tag": quality_tag,
            }
        )

records.sort(key=lambda x: x["image_id"])
mean_brightness = round(sum(x["normalized_brightness"] for x in records) / len(records), 4)

payload = {
    "image_count": len(records),
    "mean_normalized_brightness": mean_brightness,
    "records": records,
}

output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY
