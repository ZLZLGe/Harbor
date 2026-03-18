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

ALLOWED_STATUS = {"ok", "empty", "yaml_error"}


def make_null_values():
    return {path: None for path in TARGET_PATHS}


def read_nested(mapping, dotted_path):
    current = mapping
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def build_expected():
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

    return {
        "target_paths": TARGET_PATHS,
        "files": rows,
        "status_counts": status_counts,
    }


def main():
    output_path = Path("/root/outputs/parsed_values.json")
    assert output_path.exists(), "Missing /root/outputs/parsed_values.json"

    actual = json.loads(output_path.read_text(encoding="utf-8"))
    expected = build_expected()

    assert isinstance(actual, dict), "Output root must be a JSON object"
    assert set(actual.keys()) == {"target_paths", "files", "status_counts"}, "Unexpected top-level keys"

    assert actual["target_paths"] == TARGET_PATHS, "target_paths mismatch"

    assert isinstance(actual["files"], list), "files must be a list"
    assert len(actual["files"]) == len(INPUT_FILES), "files length mismatch"

    for idx, row in enumerate(actual["files"]):
        assert isinstance(row, dict), f"files[{idx}] must be an object"
        assert set(row.keys()) == {"file", "load_status", "values"}, f"Unexpected keys in files[{idx}]"
        assert row["load_status"] in ALLOWED_STATUS, f"Invalid load_status in files[{idx}]"
        assert row["file"] == INPUT_FILES[idx], f"File order mismatch at index {idx}"
        assert list(row["values"].keys()) == TARGET_PATHS, f"Value key order mismatch in files[{idx}]"

    assert actual["status_counts"] == expected["status_counts"], "status_counts mismatch"
    assert actual == expected, "Output content mismatch"

    marker = Path("/tmp/yaml_unsafe_marker")
    assert not marker.exists(), "Unsafe YAML execution marker detected"


if __name__ == "__main__":
    main()
