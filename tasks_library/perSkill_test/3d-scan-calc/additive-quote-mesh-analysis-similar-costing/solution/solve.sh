#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


def load_pricing_table(path):
    pricing = {}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            material_id = int(row["material_id"])
            pricing[material_id] = {
                "density_g_cm3": float(row["density_g_cm3"]),
                "powder_price_usd_per_kg": float(row["powder_price_usd_per_kg"]),
            }
    return pricing


analyzer = MeshAnalyzer("/root/powder_bed_scan.stl")
report = analyzer.analyze_largest_component()

material_id = report["main_part_material_id"]
part_volume_cm3 = report["main_part_volume"]

pricing_table = load_pricing_table("/root/material_pricing.csv")
material = pricing_table[material_id]

part_mass_g = part_volume_cm3 * material["density_g_cm3"]
material_cost_usd = (part_mass_g / 1000.0) * material["powder_price_usd_per_kg"]

result = {
    "material_id": material_id,
    "part_volume_cm3": part_volume_cm3,
    "part_mass_g": part_mass_g,
    "powder_unit_price_usd_per_kg": material["powder_price_usd_per_kg"],
    "material_cost_usd": material_cost_usd,
}

with open("/root/production_quote.json", "w") as handle:
    json.dump(result, handle, indent=2)
PY
