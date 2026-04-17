#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "tiles.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "spatial_report.csv"
output_dir.mkdir(parents=True, exist_ok=True)

rows = []
with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        area = float(row["area_km2"])
        pop = int(row["population"])
        elevation = float(row["elevation_m"])

        density = pop / area
        if density >= 8000:
            band = "high"
        elif density >= 6000:
            band = "medium"
        else:
            band = "low"

        rows.append(
            {
                "tile_id": row["tile_id"],
                "pop_density": f"{density:.3f}",
                "population_band": band,
                "relief_index": f"{elevation / 1000:.3f}",
            }
        )

rows.sort(key=lambda x: (-float(x["pop_density"]), x["tile_id"]))

with output_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = ["tile_id", "pop_density", "population_band", "relief_index"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
