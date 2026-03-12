#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/solve_task.py
import json
import math
import os
import sys


SKILL_PATHS = [
    "/root/.codex/skills/mesh-analysis/scripts",
    "/root/.claude/skills/mesh-analysis/scripts",
    "/root/.agents/skills/mesh-analysis/scripts",
]

for skill_path in SKILL_PATHS:
    if os.path.isdir(skill_path) and skill_path not in sys.path:
        sys.path.append(skill_path)

from mesh_tool import MeshAnalyzer


def triangle_area(triangle):
    v1, v2, v3 = triangle[:3]
    ax = v2[0] - v1[0]
    ay = v2[1] - v1[1]
    az = v2[2] - v1[2]
    bx = v3[0] - v1[0]
    by = v3[1] - v1[1]
    bz = v3[2] - v1[2]
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def component_surface_area(triangles):
    return sum(triangle_area(triangle) for triangle in triangles)


def parse_process_table(path):
    recipes = {}
    with open(path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) != 6 or parts[0] in {"Recipe ID", "---"}:
                continue
            recipe_id = int(parts[0])
            recipes[recipe_id] = {
                "dry_film_thickness_mm": float(parts[2]),
                "cured_density_g_per_cm3": float(parts[3]),
                "transfer_efficiency": float(parts[4]),
                "material_cost_usd_per_kg": float(parts[5]),
            }
    return recipes


def main():
    analyzer = MeshAnalyzer("/root/scan_data.stl")
    components = analyzer.get_components()
    if not components:
        raise RuntimeError("No connected components found in /root/scan_data.stl")

    largest_component = max(components, key=analyzer.get_volume)
    recipe_id = largest_component[0][3]
    surface_area_cm2 = component_surface_area(largest_component)

    recipes = parse_process_table("/root/coating_process_table.md")
    if recipe_id not in recipes:
        raise KeyError(f"Recipe ID {recipe_id} not found in process table")

    recipe = recipes[recipe_id]
    dry_volume_cm3 = surface_area_cm2 * (recipe["dry_film_thickness_mm"] / 10.0)
    coating_mass_g = dry_volume_cm3 * recipe["cured_density_g_per_cm3"] / recipe["transfer_efficiency"]
    coating_cost_usd = coating_mass_g / 1000.0 * recipe["material_cost_usd_per_kg"]

    result = {
        "recipe_id": recipe_id,
        "surface_area_cm2": surface_area_cm2,
        "coating_mass_g": coating_mass_g,
        "coating_cost_usd": coating_cost_usd,
    }

    with open("/root/coating_estimate.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
EOF

python3 /root/solve_task.py
