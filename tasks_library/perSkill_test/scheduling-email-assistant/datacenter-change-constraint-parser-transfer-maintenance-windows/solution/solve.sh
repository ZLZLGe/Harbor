#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import re
from pathlib import Path


INPUT_PATH = Path("/root/maintenance_threads.json")
OUTPUT_PATH = Path("/root/change_window_constraints.json")

DATE_MAP = {
    "July 11, 2026": "2026-07-11",
    "July 12, 2026": "2026-07-12",
    "July 14": "2026-07-14",
    "July 16": "2026-07-16",
    "July 18": "2026-07-18",
    "August 2, 2026": "2026-08-02",
    "August 3, 2026": "2026-08-03",
    "August 5": "2026-08-05",
    "August 7": "2026-08-07",
    "August 9": "2026-08-09",
    "August 21, 2026": "2026-08-21",
    "August 22, 2026": "2026-08-22",
    "August 24": "2026-08-24",
    "August 28": "2026-08-28",
    "August 31": "2026-08-31",
    "September 3": "2026-09-03",
    "September 6": "2026-09-06",
    "September 7, 2026": "2026-09-07",
    "September 8, 2026": "2026-09-08",
    "September 10": "2026-09-10",
}


def normalize_reason(reason: str) -> str:
    reason = reason.strip().rstrip(".")
    return reason[0].lower() + reason[1:] if reason else reason


def parse_date(month_day: str) -> str:
    if month_day not in DATE_MAP:
        raise ValueError(f"Unmapped date text: {month_day}")
    return DATE_MAP[month_day]


def parse_windows(thread):
    windows = []
    approved_bodies = []
    for entry in thread:
        body = entry["body"]
        lowered = body.lower()
        if "approved" in lowered or lowered.startswith("approve ") or "proceed with" in lowered:
            approved_bodies.append(body)
    for body in approved_bodies:
        for match in re.finditer(
            r"(July|August|September) (\d{1,2}), (\d{4}) "
            r"(?:from )?(\d{2}:\d{2})\s*(?:to|-)\s*(\d{2}:\d{2}) ([A-Z]{3,4})",
            body,
        ):
            month, day, year, start_time, end_time, timezone = match.groups()
            date = parse_date(f"{month} {int(day)}, {year}")
            windows.append(
                {
                    "start_date": date,
                    "end_date": date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "timezone": timezone,
                }
            )
    unique = {
        (item["start_date"], item["start_time"], item["end_time"], item["timezone"]): item
        for item in windows
    }
    return sorted(unique.values(), key=lambda item: (item["start_date"], item["start_time"]))


def parse_freezes(thread):
    freezes = []
    for entry in thread:
        body = entry["body"]
        patterns = [
            (
                r"(July) (\d{1,2}) through July (\d{1,2}) is frozen for (.+?)(?:,|\.|$)",
                lambda groups: (groups[0], groups[1], groups[2], normalize_reason(groups[3])),
            ),
            (
                r"No-change freeze runs (August) (\d{1,2}) to August (\d{1,2}) for (.+?)(?:\.|$)",
                lambda groups: (groups[0], groups[1], groups[2], normalize_reason(groups[3])),
            ),
            (
                r"Month-end freeze is (August) (\d{1,2}) through August (\d{1,2})(?:\.|$)",
                lambda groups: (groups[0], groups[1], groups[2], "month-end freeze"),
            ),
            (
                r"regional freeze from (September) (\d{1,2}) to September (\d{1,2}) for (.+?)(?:\.|$)",
                lambda groups: (groups[0], groups[1], groups[2], normalize_reason(groups[3])),
            ),
        ]
        for pattern, transform in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if not match:
                continue
            month, start_day, end_day, reason = transform(match.groups())
            freezes.append(
                {
                    "start_date": parse_date(f"{month} {int(start_day)}"),
                    "end_date": parse_date(f"{month} {int(end_day)}"),
                    "reason": reason,
                }
            )
            break
    return sorted(freezes, key=lambda item: item["start_date"])


def parse_prohibited_dates(thread):
    blocked = []
    for entry in thread:
        body = entry["body"]
        patterns = [
            r"(July|August|September) (\d{1,2}) is blocked because of (.+?)(?:\.|$)",
            r"do not touch (July|August|September) (\d{1,2}) because (.+?)(?:\.|$)",
            r"(August|September) (\d{1,2}) is off limits because (.+?)(?:\.|$)",
            r"(September|August|July) (\d{1,2}) is blocked for (.+?)(?:\.|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                month, day, reason = match.groups()
                blocked.append(
                    {
                        "date": parse_date(f"{month} {int(day)}"),
                        "reason": normalize_reason(reason),
                    }
                )
                break
    unique = {(item["date"], item["reason"]): item for item in blocked}
    return sorted(unique.values(), key=lambda item: item["date"])


def parse_outage_minutes(thread):
    for entry in thread:
        body = entry["body"]
        match = re.search(
            r"(?:under|at most|cap at|within|ceiling at|maximum outage of) (\d+) minutes",
            body,
        )
        if match:
            return int(match.group(1))
    raise ValueError("Missing maximum outage minutes")


def parse_sequences(thread):
    sequences = []
    for entry in thread:
        body = entry["body"]
        if "before" not in body:
            continue
        for sentence in re.split(r"(?<=\.)\s+", body):
            sentence = sentence.strip()
            if "before" in sentence and not sentence.startswith("Approved") and "approved" not in sentence.lower():
                cleaned = sentence.rstrip(".")
                sequences.append(cleaned + ".")
    return sequences


with INPUT_PATH.open("r", encoding="utf-8") as f:
    source = json.load(f)

result = {"changes": []}
for change in sorted(source["changes"], key=lambda item: item["change_id"]):
    thread = change["approval_thread"]
    result["changes"].append(
        {
            "change_id": change["change_id"],
            "system": change["system"],
            "approved_windows": parse_windows(thread),
            "freeze_periods": parse_freezes(thread),
            "prohibited_dates": parse_prohibited_dates(thread),
            "maximum_outage_minutes": parse_outage_minutes(thread),
            "sequencing_constraints": parse_sequences(thread),
        }
    )

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY
