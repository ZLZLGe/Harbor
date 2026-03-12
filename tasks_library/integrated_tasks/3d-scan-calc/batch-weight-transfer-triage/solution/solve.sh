#!/bin/bash
set -e

python3 - <<'PY'
import json
import os
import re
import sys

skill_paths = [
    "/root/.codex/skills/mesh-analysis/scripts",
    "/root/.claude/skills/mesh-analysis/scripts",
]
for skill_path in skill_paths:
    if os.path.exists(skill_path):
        sys.path.append(skill_path)

from mesh_tool import MeshAnalyzer


def load_density_table(path):
    table = {}
    pattern = re.compile(r"^\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|")
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.match(line.strip())
            if match:
                table[int(match.group(1))] = float(match.group(2))
    return table


def load_policy(path):
    approved_ids = []
    max_mass = None
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            id_match = re.match(r"^-\s*`(\d+)`$", line)
            if id_match:
                approved_ids.append(int(id_match.group(1)))
            mass_match = re.search(r"`([0-9]+(?:\.[0-9]+)?)\s*g`", line)
            if mass_match:
                max_mass = float(mass_match.group(1))
    return set(approved_ids), max_mass


def analyze_scan(path, density_table, approved_ids, max_mass):
    analyzer = MeshAnalyzer(path)
    report = analyzer.analyze_largest_component()
    material_id = report["main_part_material_id"]
    density = density_table[material_id]
    mass = report["main_part_volume"] * density
    return {
        "file": os.path.basename(path),
        "main_part_mass": mass,
        "material_id": material_id,
        "acceptable": material_id in approved_ids and mass <= max_mass,
    }


density_table = load_density_table("/root/material_density_table.md")
approved_ids, max_mass = load_policy("/root/batch_acceptance_rules.md")

ranked_parts = []
for name in sorted(os.listdir("/root/scan_batch")):
    if not name.endswith(".stl"):
        continue
    ranked_parts.append(
        analyze_scan(
            os.path.join("/root/scan_batch", name),
            density_table,
            approved_ids,
            max_mass,
        )
    )

ranked_parts.sort(key=lambda item: (-item["main_part_mass"], item["file"]))
acceptable_parts = [item for item in ranked_parts if item["acceptable"]]
if not acceptable_parts:
    raise RuntimeError("No acceptable scans found in batch")

heaviest = acceptable_parts[0]
result = {
    "heaviest_acceptable": {
        "file": heaviest["file"],
        "main_part_mass": heaviest["main_part_mass"],
        "material_id": heaviest["material_id"],
    },
    "ranked_parts": ranked_parts,
}

with open("/root/batch_triage.json", "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
PY
