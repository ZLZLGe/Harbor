#!/bin/bash
set -e

cat <<'EOF' > /root/solve_task.py
import json
import sys
import tomllib

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


def load_alloys():
    with open("/root/alloy_registry.json") as handle:
        payload = json.load(handle)
    return {entry["alloy_id"]: entry for entry in payload["alloys"]}


def main():
    analyzer = MeshAnalyzer("/root/subsea_recovery_scan.stl")
    report = analyzer.analyze_largest_component()

    alloy_id = report["main_part_material_id"]
    volume_cm3 = report["main_part_volume"]
    volume_m3 = volume_cm3 / 1_000_000.0

    alloys = load_alloys()
    density_kg_m3 = alloys[alloy_id]["density_kg_m3"]

    with open("/root/recovery_factors.toml", "rb") as handle:
        factors = tomllib.load(handle)

    gravity = factors["hydrostatics"]["gravity_m_s2"]
    seawater_density = factors["hydrostatics"]["seawater_density_kg_m3"]
    dynamic_factor = factors["rigging"]["dynamic_amplification_factor"]

    dry_weight_kN = volume_m3 * density_kg_m3 * gravity / 1000.0
    underwater_lift_load_kN = (
        volume_m3
        * (density_kg_m3 - seawater_density)
        * gravity
        / 1000.0
        * dynamic_factor
    )

    result = {
        "alloy_id": alloy_id,
        "main_body_volume_m3": volume_m3,
        "dry_weight_kN": dry_weight_kN,
        "underwater_lift_load_kN": underwater_lift_load_kN,
    }

    with open("/root/lift_plan.json", "w") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
EOF

python3 /root/solve_task.py
