#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/solve_task.py
import json
import re
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


def load_density_table():
    densities = {}
    with open("/root/material_density_table.md", encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"\|\s*\**(\d+)\**\s*\|\s*[^|]+\|\s*([0-9.]+)\s*\|", line)
            if match:
                densities[int(match.group(1))] = float(match.group(2))
    return densities


def analyze_scan(path):
    analyzer = MeshAnalyzer(path)
    report = analyzer.analyze_largest_component()
    return report["main_part_volume"], report["main_part_material_id"]


def main():
    densities = load_density_table()

    pre_volume, pre_material_id = analyze_scan("/root/pre_machining_scan.stl")
    post_volume, post_material_id = analyze_scan("/root/post_machining_scan.stl")

    if pre_material_id != post_material_id:
        raise RuntimeError(
            f"Main component material mismatch: pre={pre_material_id}, post={post_material_id}"
        )

    if pre_material_id not in densities:
        raise RuntimeError(f"Material ID {pre_material_id} not found in density table")

    density = densities[pre_material_id]
    pre_mass = pre_volume * density
    post_mass = post_volume * density

    result = {
        "material_id": pre_material_id,
        "pre_machining_volume_cm3": pre_volume,
        "post_machining_volume_cm3": post_volume,
        "pre_machining_mass_g": pre_mass,
        "post_machining_mass_g": post_mass,
        "removed_mass_g": pre_mass - post_mass,
        "yield_percentage": (post_mass / pre_mass) * 100.0,
    }

    with open("/root/yield_loss_report.json", "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
EOF

python3 /root/solve_task.py
