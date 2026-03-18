#!/bin/bash
set -euo pipefail

cat <<'PY' > /root/solve_task.py
import json
import os
import re
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


def load_density_table(filepath: str):
    mapping = {}
    pattern = re.compile(r"\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*([0-9.]+)\s*\|")
    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.search(line)
            if match:
                mapping[int(match.group(1))] = float(match.group(2))
    return mapping


def main() -> None:
    analyzer = MeshAnalyzer("/root/scan_data.stl")
    report = analyzer.analyze_largest_component()
    density_table = load_density_table("/root/material_density_table.md")
    material_id = report["main_part_material_id"]
    density = density_table[material_id]
    volume = report["main_part_volume"]
    payload = {
        "main_part_volume": volume,
        "main_part_material_id": material_id,
        "density": density,
        "main_part_mass": volume * density,
    }
    os.makedirs("/root/outputs", exist_ok=True)
    with open("/root/outputs/main_part_mass.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /root/solve_task.py
