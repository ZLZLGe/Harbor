#!/bin/bash
set -e

python3 - <<'PY'
import csv
import json
import os
import statistics
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "light_curve.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "signal_report.json"
output_dir.mkdir(parents=True, exist_ok=True)

points = []
with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        points.append({"time": float(row["time"]), "flux": float(row["flux"])})

flux_values = [p["flux"] for p in points]
peak_times = [p["time"] for p in sorted(points, key=lambda p: (-p["flux"], p["time"]))[:2]]

report = {
    "series_id": "template-series-01",
    "n_points": len(points),
    "mean_flux": round(sum(flux_values) / len(flux_values), 6),
    "std_flux": round(statistics.pstdev(flux_values), 6),
    "min_flux": min(flux_values),
    "max_flux": max(flux_values),
    "top_peak_times": peak_times,
}

output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
PY
