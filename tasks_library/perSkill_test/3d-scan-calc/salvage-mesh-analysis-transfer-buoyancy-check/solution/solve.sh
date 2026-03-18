#!/bin/bash
set -euo pipefail

cat <<'PY' > /root/solve_task.py
import json
import re
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


REFERENCE_PATH = "/root/salvage_density_reference.md"
SCAN_PATH = "/root/recovered_artifact_scan.stl"
OUTPUT_PATH = "/root/buoyancy_report.json"


def load_reference_tables(path):
    material_density = {}
    fluid_density = {}

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue

            cols = [col.strip() for col in line.strip("|").split("|")]
            if len(cols) < 2:
                continue

            if len(cols) >= 3 and re.fullmatch(r"\d+", cols[0]) and re.fullmatch(r"\d+(?:\.\d+)?", cols[2]):
                material_density[int(cols[0])] = float(cols[2])
                continue

            if cols[0] and re.fullmatch(r"\d+(?:\.\d+)?", cols[1]):
                fluid_density[cols[0].lower()] = float(cols[1])

    if not material_density:
        raise ValueError("Failed to parse artifact material densities")
    if "seawater" not in fluid_density:
        raise ValueError("Failed to parse seawater density")

    return material_density, fluid_density


def main():
    analyzer = MeshAnalyzer(SCAN_PATH)
    report = analyzer.analyze_largest_component()

    volume_cm3 = report["main_part_volume"]
    material_id = report["main_part_material_id"]

    material_density, fluid_density = load_reference_tables(REFERENCE_PATH)
    if material_id not in material_density:
        raise ValueError(f"Material ID {material_id} missing from reference")

    artifact_density = material_density[material_id]
    seawater_density = fluid_density["seawater"]

    artifact_mass = volume_cm3 * artifact_density
    displaced_seawater_mass = volume_cm3 * seawater_density
    buoyancy_margin = displaced_seawater_mass - artifact_mass
    seawater_result = "floats" if buoyancy_margin > 0 else "sinks"

    result = {
        "material_id": material_id,
        "main_component_volume_cm3": volume_cm3,
        "artifact_density_g_cm3": artifact_density,
        "seawater_density_g_cm3": seawater_density,
        "artifact_mass_g": artifact_mass,
        "displaced_seawater_mass_g": displaced_seawater_mass,
        "buoyancy_margin_g": buoyancy_margin,
        "seawater_result": seawater_result,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /root/solve_task.py
