#!/bin/bash
set -euo pipefail

cat <<'PY' > /root/solve_task.py
import json
import re
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


SCAN_PATH = "/root/mold_insert_scan_ascii.stl"
PROCESS_SHEET_PATH = "/root/silicone_process_sheet.md"
OUTPUT_PATH = "/root/silicone_pour_plan.json"


def load_process_sheet(path):
    values = {}

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue

            cols = [col.strip() for col in line.strip("|").split("|")]
            if len(cols) != 3:
                continue
            if cols[0] == "Parameter" or cols[0] == "---":
                continue

            name = cols[0].lower()
            number_match = re.search(r"-?\d+(?:\.\d+)?", cols[1])
            if not number_match:
                continue

            values[name] = float(number_match.group(0))

    required = {"transfer factor", "reserve percent", "fixed loss"}
    missing = required.difference(values)
    if missing:
        raise ValueError(f"Missing process sheet values: {sorted(missing)}")

    return values


def main():
    analyzer = MeshAnalyzer(SCAN_PATH)
    report = analyzer.analyze_largest_component()
    main_component_volume_cm3 = report["main_part_volume"]

    process_values = load_process_sheet(PROCESS_SHEET_PATH)
    transfer_factor = process_values["transfer factor"]
    reserve_percent = process_values["reserve percent"] / 100.0
    fixed_loss_ml = process_values["fixed loss"]

    net_fill_volume_ml = main_component_volume_cm3 * transfer_factor
    reserve_volume_ml = net_fill_volume_ml * reserve_percent + fixed_loss_ml
    total_silicone_required_ml = net_fill_volume_ml + reserve_volume_ml

    result = {
        "main_component_volume_cm3": main_component_volume_cm3,
        "net_fill_volume_ml": net_fill_volume_ml,
        "reserve_volume_ml": reserve_volume_ml,
        "total_silicone_required_ml": total_silicone_required_ml,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /root/solve_task.py
