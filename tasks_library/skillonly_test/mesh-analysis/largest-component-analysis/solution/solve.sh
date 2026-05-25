#!/bin/bash
set -euo pipefail

cat <<'PY' > /root/solve_task.py
import json
import os
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


def main() -> None:
    analyzer = MeshAnalyzer("/root/scan_data.stl")
    report = analyzer.analyze_largest_component()
    payload = {
        "main_part_volume": report["main_part_volume"],
        "main_part_material_id": report["main_part_material_id"],
        "total_components": report["total_components"],
    }
    os.makedirs("/root/outputs", exist_ok=True)
    with open("/root/outputs/largest_component_report.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /root/solve_task.py
