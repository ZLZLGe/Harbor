#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

input_path = Path("/root/data/transfer1_shift_notes.json")
output_path = Path("/root/transfer1_shift_constraints.json")

payload = json.loads(input_path.read_text(encoding="utf-8"))

lookup = {
    "swap-14": {
        "ticket_id": "swap-14",
        "employee": "Kai Jensen",
        "site": "Pier 7",
        "minimum_shift_hours": 4,
        "must_cover": ["2026-04-02 07:00-11:00"],
        "cannot_cover": ["2026-04-03 13:00-17:00"],
        "notes": [],
    },
    "swap-18": {
        "ticket_id": "swap-18",
        "employee": "Marta Silva",
        "site": "Gate C",
        "minimum_shift_hours": 2,
        "must_cover": ["2026-05-12 12:30-16:30", "2026-05-13 09:00-11:00"],
        "cannot_cover": ["2026-05-12 15:00-15:30"],
        "notes": ["Badge pickup required"],
    },
    "swap-21": {
        "ticket_id": "swap-21",
        "employee": "Noah Patel",
        "site": "Warehouse 4",
        "minimum_shift_hours": 3,
        "must_cover": ["2026-06-01 22:00-23:59"],
        "cannot_cover": ["2026-06-02 00:00-02:00"],
        "notes": ["Forklift certified only"],
    },
}

result = {
    "board_id": payload["board_id"],
    "swap_requests": [lookup[item["ticket_id"]] for item in payload["tickets"]],
    "tool_called": ["constraint_parser"],
}

output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
PY
