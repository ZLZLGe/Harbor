#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import sys
import tomllib

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


def load_catalog(path):
    catalog = {}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            catalog[int(row["ore_type_id"])] = {
                "bulk_density_t_per_m3": float(row["bulk_density_t_per_m3"]),
                "fe_grade_pct": float(row["fe_grade_pct"]),
                "silica_pct": float(row["silica_pct"]),
            }
    return catalog


analyzer = MeshAnalyzer("/root/conveyor_ore_scan.stl")
report = analyzer.analyze_largest_component()

ore_type_id = report["main_part_material_id"]
main_ore_volume_m3 = report["main_part_volume"] / 1_000_000.0

catalog = load_catalog("/root/ore_type_catalog.csv")
ore = catalog[ore_type_id]
estimated_mass_tonnes = main_ore_volume_m3 * ore["bulk_density_t_per_m3"]

with open("/root/routing_rules.toml", "rb") as handle:
    rules = tomllib.load(handle)

selected_route = None
for route in rules["routes"]:
    if (
        ore["fe_grade_pct"] >= route["min_fe_grade_pct"]
        and ore["silica_pct"] <= route["max_silica_pct"]
        and estimated_mass_tonnes <= route["max_mass_tonnes"]
    ):
        selected_route = route
        break

if selected_route is None:
    raise RuntimeError("No routing rule matched the extracted ore parcel")

result = {
    "ore_type_id": ore_type_id,
    "main_ore_volume_m3": main_ore_volume_m3,
    "estimated_mass_tonnes": estimated_mass_tonnes,
    "dispatch_line": selected_route["dispatch_line"],
    "diversion_gate": selected_route["diversion_gate"],
    "requires_breaker": estimated_mass_tonnes >= rules["breaker"]["threshold_tonnes"],
}

with open("/root/ore_manifest.json", "w") as handle:
    json.dump(result, handle, indent=2)
PY
