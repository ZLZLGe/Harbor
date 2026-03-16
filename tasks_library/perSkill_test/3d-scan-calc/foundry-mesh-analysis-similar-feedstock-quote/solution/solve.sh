#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/solve_task.py
import json
import os
import re
import sys


def add_skill_path():
    candidates = [
        "/root/.codex/skills/mesh-analysis/scripts",
        "/root/.claude/skills/mesh-analysis/scripts",
        "/root/.agents/skills/mesh-analysis/scripts",
        "/root/.goose/skills/mesh-analysis/scripts",
        "/root/.factory/skills/mesh-analysis/scripts",
        "/root/.gemini/skills/mesh-analysis/scripts",
        "/root/.opencode/skill/mesh-analysis/scripts",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            sys.path.append(candidate)
            return
    raise FileNotFoundError("mesh-analysis skill scripts directory not found")


def parse_density_table(path):
    density_table = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            cols = [col.strip() for col in line.strip("|").split("|")]
            if len(cols) < 3:
                continue
            alloy_match = re.fullmatch(r"\d+", cols[0])
            density_match = re.fullmatch(r"\d+(?:\.\d+)?", cols[2])
            if alloy_match and density_match:
                density_table[int(cols[0])] = float(cols[2])
    return density_table


def parse_cost_table(path):
    cost_table = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            cols = [col.strip() for col in line.strip("|").split("|")]
            if len(cols) < 3:
                continue
            alloy_match = re.fullmatch(r"\d+", cols[0])
            usd_match = re.fullmatch(r"\d+(?:\.\d+)?", cols[1])
            multiplier_match = re.fullmatch(r"\d+(?:\.\d+)?", cols[2])
            if alloy_match and usd_match and multiplier_match:
                cost_table[int(cols[0])] = (float(cols[1]), float(cols[2]))
    return cost_table


def main():
    add_skill_path()
    from mesh_tool import MeshAnalyzer

    density_table = parse_density_table("/root/alloy_density_table.md")
    cost_table = parse_cost_table("/root/feedstock_cost_table.md")

    analyzer = MeshAnalyzer("/root/foundry_scan.stl")
    report = analyzer.analyze_largest_component()

    alloy_code = report["main_part_material_id"]
    volume_cm3 = report["main_part_volume"]

    if alloy_code not in density_table:
        raise KeyError(f"Alloy code {alloy_code} not found in density table")
    if alloy_code not in cost_table:
        raise KeyError(f"Alloy code {alloy_code} not found in cost table")

    density_g_per_cm3 = density_table[alloy_code]
    usd_per_kg, melt_loss_multiplier = cost_table[alloy_code]

    feedstock_mass_kg = volume_cm3 * density_g_per_cm3 / 1000.0
    feedstock_quote_usd = feedstock_mass_kg * usd_per_kg * melt_loss_multiplier

    result = {
        "alloy_code": alloy_code,
        "main_component_volume_cm3": volume_cm3,
        "feedstock_mass_kg": feedstock_mass_kg,
        "feedstock_quote_usd": feedstock_quote_usd,
    }

    with open("/root/feedstock_quote.json", "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
EOF

python3 /root/solve_task.py
