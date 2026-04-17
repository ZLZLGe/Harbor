#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import os
from pathlib import Path


def normalize_token(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "react_test_requests.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "react_test_plan.csv"
output_dir.mkdir(parents=True, exist_ok=True)

rows = []

with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        case_id = (row.get("case_id") or "").strip()
        channel = normalize_token(row.get("channel") or "") or "source"
        variant = normalize_token(row.get("variant") or "")
        pattern = (row.get("pattern") or "").strip()
        needs_gate = normalize_token(row.get("needs_gate") or "")
        flag_name = (row.get("flag_name") or "").strip()
        scenario = normalize_token(row.get("scenario") or "")

        is_www = channel == "www"
        is_variant_false = is_www and variant == "false"

        if channel == "experimental":
            command = f"yarn test -r=experimental --silent --no-watchman {pattern}"
            expected_channel_state = "experimental-enabled"
            gated_flag_check = f"{flag_name}=experimental-on"
        elif channel == "stable":
            command = f"yarn test-stable --silent --no-watchman {pattern}"
            expected_channel_state = "stable-release"
            gated_flag_check = f"{flag_name}=stable-default"
        elif channel == "classic":
            command = f"yarn test-classic --silent --no-watchman {pattern}"
            expected_channel_state = "www-classic"
            gated_flag_check = f"{flag_name}=classic-default"
        elif is_www and is_variant_false:
            command = f"yarn test-www --variant=false --silent --no-watchman {pattern}"
            expected_channel_state = "www-modern-variant-false"
            gated_flag_check = f"{flag_name}=variant:false"
        elif is_www:
            command = f"yarn test-www --silent --no-watchman {pattern}"
            expected_channel_state = "www-modern-variant-true"
            gated_flag_check = f"{flag_name}=variant:true"
        else:
            command = f"yarn test --silent --no-watchman {pattern}"
            expected_channel_state = "source-default"
            gated_flag_check = f"{flag_name}=source-default"

        if needs_gate == "yes" and scenario == "unavailable_without_flag":
            gate_strategy = f"@gate {flag_name}"
            notes = "skip unless flag enabled"
            flag_check = gated_flag_check
        elif needs_gate == "yes" and scenario == "behavior_differs_by_flag":
            gate_strategy = "gate()"
            notes = "assert both flag branches"
            flag_check = gated_flag_check
        else:
            gate_strategy = "none"
            notes = "baseline route"
            flag_check = "not-needed"

        rows.append(
            {
                "case_id": case_id,
                "command": command,
                "gate_strategy": gate_strategy,
                "flag_check": flag_check,
                "expected_channel_state": expected_channel_state,
                "notes": notes,
            }
        )

rows.sort(key=lambda item: item["case_id"])

with output_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = [
        "case_id",
        "command",
        "gate_strategy",
        "flag_check",
        "expected_channel_state",
        "notes",
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
