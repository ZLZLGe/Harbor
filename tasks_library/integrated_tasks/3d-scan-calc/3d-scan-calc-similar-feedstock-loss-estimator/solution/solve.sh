#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/solve_task.py
import json
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


DENSITY_TABLE = {
    1: 0.10,
    10: 7.85,
    25: 2.70,
    42: 5.55,
    99: 11.34,
}

WASTE_FACTORS = {
    1: 0.50,
    10: 0.08,
    25: 0.06,
    42: 0.12,
    99: 0.15,
}


def main():
    analyzer = MeshAnalyzer("/root/scan_data.stl")
    report = analyzer.analyze_largest_component()

    volume = report["main_part_volume"]
    material_id = report["main_part_material_id"]

    if material_id not in DENSITY_TABLE:
        raise SystemExit(f"Unknown material ID for density lookup: {material_id}")
    if material_id not in WASTE_FACTORS:
        raise SystemExit(f"Unknown material ID for waste factor lookup: {material_id}")

    net_part_mass = volume * DENSITY_TABLE[material_id]
    waste_factor = WASTE_FACTORS[material_id]
    required_feedstock_mass = net_part_mass / (1.0 - waste_factor)
    estimated_waste_mass = required_feedstock_mass - net_part_mass

    result = {
        "material_id": material_id,
        "net_part_mass": net_part_mass,
        "waste_factor": waste_factor,
        "required_feedstock_mass": required_feedstock_mass,
        "estimated_waste_mass": estimated_waste_mass,
    }

    with open("/root/feedstock_plan.json", "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
EOF

python3 /root/solve_task.py
