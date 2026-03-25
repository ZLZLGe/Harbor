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


def load_events(path: str | Path):
    events = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                events.append(json.loads(line))
    return events


def build_rollups(events):
    grouped_events = {}
    session_order = []

    for event in events:
        session_id = str(event["session_id"])
        if session_id not in grouped_events:
            grouped_events[session_id] = []
            session_order.append(session_id)
        grouped_events[session_id].append(event)

    rows = []
    for session_id in session_order:
        session_events = grouped_events[session_id]
        first_event = session_events[0]
        last_event = session_events[-1]
        rows.append(
            {
                "session_id": session_id,
                "user_id": str(first_event["user_id"]),
                "event_count": len(session_events),
                "session_duration_seconds": int(last_event["event_time"]) - int(first_event["event_time"]),
                "entry_page": str(first_event["page"]),
                "converted": 1 if any(event["event_type"] == "purchase" for event in session_events) else 0,
            }
        )
    return rows


def write_rollups(rows, output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline clickstream session rollup.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    events = load_events(args.input)
    rows = build_rollups(events)
    write_rollups(rows, args.output)


if __name__ == "__main__":
    main()
