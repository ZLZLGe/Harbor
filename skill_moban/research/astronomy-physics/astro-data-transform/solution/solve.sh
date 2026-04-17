#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "observations.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "summary.csv"
output_dir.mkdir(parents=True, exist_ok=True)

rows = []
with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        quality = row.get("quality_flag", "")
        if quality == "drop":
            continue

        flux_raw = (row.get("flux_jy") or "").strip()
        dist_raw = (row.get("distance_pc") or "").strip()

        flux_value = float(flux_raw) if flux_raw else None
        dist_value = float(dist_raw) if dist_raw else None

        flux_mjy = f"{flux_value * 1000:.3f}" if flux_value is not None else ""
        if flux_value is not None and dist_value is not None:
            luminosity_proxy = f"{flux_value * (dist_value ** 2):.4f}"
        else:
            luminosity_proxy = ""

        rows.append(
            {
                "object_id": row["object_id"],
                "flux_mjy": flux_mjy,
                "luminosity_proxy": luminosity_proxy,
                "quality_flag": quality,
            }
        )

rows.sort(key=lambda x: x["object_id"])

with output_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = ["object_id", "flux_mjy", "luminosity_proxy", "quality_flag"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
