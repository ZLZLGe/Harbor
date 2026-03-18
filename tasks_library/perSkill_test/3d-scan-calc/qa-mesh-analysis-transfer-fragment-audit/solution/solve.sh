#!/bin/bash
set -euo pipefail

cat <<'PY' > /root/solve_task.py
import json
import re
import sys

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


SCAN_PATH = "/root/fragment_audit_scan.stl"
POLICY_PATH = "/root/fragment_cleanliness_policy.md"
OUTPUT_PATH = "/root/fragment_audit.json"


def load_threshold(path):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    match = re.search(r"Max debris-volume ratio\s*\|\s*([0-9]+(?:\.[0-9]+)?)%", text)
    if not match:
        raise ValueError("Could not find debris-volume threshold in policy file")

    return float(match.group(1)) / 100.0


def main():
    analyzer = MeshAnalyzer(SCAN_PATH)
    components = analyzer.get_components()
    if not components:
        raise ValueError("No connected components found in scan")

    component_volumes = [analyzer.get_volume(component) for component in components]
    component_count = len(component_volumes)
    fragment_count = component_count - 1

    main_assembly_volume_cm3 = max(component_volumes)
    total_volume_cm3 = sum(component_volumes)
    debris_volume_cm3 = total_volume_cm3 - main_assembly_volume_cm3

    fragment_count_ratio = fragment_count / component_count
    debris_volume_ratio = debris_volume_cm3 / total_volume_cm3 if total_volume_cm3 else 0.0

    cleanliness_threshold = load_threshold(POLICY_PATH)

    result = {
        "component_count": component_count,
        "fragment_count": fragment_count,
        "fragment_count_ratio": fragment_count_ratio,
        "main_assembly_volume_cm3": main_assembly_volume_cm3,
        "debris_volume_cm3": debris_volume_cm3,
        "debris_volume_ratio": debris_volume_ratio,
        "cleanliness_threshold": cleanliness_threshold,
        "passes_cleanliness_threshold": debris_volume_ratio <= cleanliness_threshold,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /root/solve_task.py
