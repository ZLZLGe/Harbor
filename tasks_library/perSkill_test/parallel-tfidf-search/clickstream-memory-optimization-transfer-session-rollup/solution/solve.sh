#!/bin/bash
set -euo pipefail

cat > /root/workspace/session_rollup_solution.py <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDNAMES = [
    "session_id",
    "user_id",
    "event_count",
    "session_duration_seconds",
    "entry_page",
    "converted",
]


def _finalize_session(state: dict[str, object]) -> dict[str, object]:
    return {
        "session_id": state["session_id"],
        "user_id": state["user_id"],
        "event_count": state["event_count"],
        "session_duration_seconds": int(state["last_event_time"]) - int(state["first_event_time"]),
        "entry_page": state["entry_page"],
        "converted": 1 if state["converted"] else 0,
    }


def rollup_clickstream(input_path: str | Path, output_path: str | Path) -> None:
    current_session: dict[str, object] | None = None

    with Path(input_path).open(encoding="utf-8") as source, Path(output_path).open(
        "w", encoding="utf-8", newline=""
    ) as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDNAMES)
        writer.writeheader()

        for line in source:
            if not line.strip():
                continue
            event = json.loads(line)
            session_id = str(event["session_id"])
            event_time = int(event["event_time"])

            if current_session is None or session_id != current_session["session_id"]:
                if current_session is not None:
                    writer.writerow(_finalize_session(current_session))
                current_session = {
                    "session_id": session_id,
                    "user_id": str(event["user_id"]),
                    "event_count": 1,
                    "first_event_time": event_time,
                    "last_event_time": event_time,
                    "entry_page": str(event["page"]),
                    "converted": event["event_type"] == "purchase",
                }
                continue

            current_session["event_count"] = int(current_session["event_count"]) + 1
            current_session["last_event_time"] = event_time
            if event["event_type"] == "purchase":
                current_session["converted"] = True

        if current_session is not None:
            writer.writerow(_finalize_session(current_session))


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream a clickstream into session rollups.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rollup_clickstream(args.input, args.output)


if __name__ == "__main__":
    main()
PY

chmod +x /root/workspace/session_rollup_solution.py
