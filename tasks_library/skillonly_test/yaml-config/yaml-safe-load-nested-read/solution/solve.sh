#!/bin/bash
set -euo pipefail

mkdir -p /root/outputs

python3 - <<'PY'
import json
from pathlib import Path

import yaml

TARGET_PATHS = [
    "telemetry.sampling.hz",
    "control.pid.lateral.kp",
    "control.pid.lateral.ki",
    "safety.fallback.mode",
]

INPUT_FILES = [
    "configs/region_north.yaml",
    "configs/region_south.yaml",
    "configs/region_empty.yaml",
    "configs/region_legacy.yaml",
]


def make_null_values():
    return {path: None for path in TARGET_PATHS}


def read_nested(mapping, dotted_path):
    current = mapping
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


rows = []
status_counts = {"ok": 0, "empty": 0, "yaml_error": 0}

for relative_path in INPUT_FILES:
    absolute_path = Path("/root") / relative_path
    try:
        with absolute_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except yaml.YAMLError:
        row = {
            "file": relative_path,
            "load_status": "yaml_error",
            "values": make_null_values(),
        }
    else:
        if loaded is None:
            row = {
                "file": relative_path,
                "load_status": "empty",
                "values": make_null_values(),
            }
        elif not isinstance(loaded, dict):
            row = {
                "file": relative_path,
                "load_status": "yaml_error",
                "values": make_null_values(),
            }
        else:
            row = {
                "file": relative_path,
                "load_status": "ok",
                "values": {path: read_nested(loaded, path) for path in TARGET_PATHS},
            }

    status_counts[row["load_status"]] += 1
    rows.append(row)

result = {
    "target_paths": TARGET_PATHS,
    "files": rows,
    "status_counts": status_counts,
}

output_path = Path("/root/outputs/parsed_values.json")
output_path.write_text(json.dumps(result, indent=2, sort_keys=False) + "\n", encoding="utf-8")
PY
