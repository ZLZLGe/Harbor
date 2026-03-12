#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
import re
import sys


def add_skill_path():
    candidates = [
        "/root/.codex/skills/mesh-analysis/scripts",
        "/root/.claude/skills/mesh-analysis/scripts",
        "/root/.agents/skills/mesh-analysis/scripts",
        "/root/.gemini/skills/mesh-analysis/scripts",
        "/root/.goose/skills/mesh-analysis/scripts",
        "/root/.factory/skills/mesh-analysis/scripts",
        "/root/.opencode/skill/mesh-analysis/scripts",
    ]
    for path in candidates:
        if os.path.exists(os.path.join(path, "mesh_tool.py")):
            sys.path.append(path)
            return
    raise RuntimeError("mesh-analysis script path not found")


def load_density_table(path):
    table = {}
    pattern = re.compile(r"^\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|")
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.match(line.strip())
            if match:
                table[int(match.group(1))] = float(match.group(2))
    if not table:
        raise RuntimeError("density table is empty")
    return table


add_skill_path()
from mesh_tool import MeshAnalyzer

density_table = load_density_table("/root/material_density_table.md")
analyzer = MeshAnalyzer("/root/audit_scan.stl")
components = analyzer.get_components()
if not components:
    raise RuntimeError("no mesh components found")

component_records = []
for component in components:
    component_records.append(
        {
            "volume": analyzer.get_volume(component),
            "material_id": component[0][3],
        }
    )

component_records.sort(key=lambda item: item["volume"], reverse=True)
main = component_records[0]
main_material_id = main["material_id"]
if main_material_id not in density_table:
    raise RuntimeError(f"material id {main_material_id} missing from density table")

discarded_debris_volume = sum(item["volume"] for item in component_records[1:])
total_volume = main["volume"] + discarded_debris_volume
scrap_percentage = 0.0 if total_volume == 0 else discarded_debris_volume / total_volume * 100.0

result = {
    "main_part_mass": main["volume"] * density_table[main_material_id],
    "material_id": main_material_id,
    "discarded_debris_volume": discarded_debris_volume,
    "scrap_percentage": scrap_percentage,
}

with open("/root/part_audit.json", "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
PY
