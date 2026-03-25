#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path("/root")


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_seat_map(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            rows.append(row)
    return rows


def load_checkins(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                {
                    "attendee_id": row["attendee_id"],
                    "meeting_id": row["meeting_id"],
                    "seat_id": row["seat_id"],
                    "slot_start": int(row["slot_start"]),
                    "slot_end": int(row["slot_end"]),
                }
            )
    return rows


def build_csr(dense: np.ndarray):
    indices = []
    data = []
    indptr = [0]
    for row in dense:
        cols = np.flatnonzero(row)
        indices.extend(int(col) for col in cols)
        data.extend([1] * len(cols))
        indptr.append(len(indices))
    return (
        np.asarray(data, dtype=np.uint8),
        np.asarray(indices, dtype=np.int64),
        np.asarray(indptr, dtype=np.int64),
    )


manifest = load_json(ROOT / "conference_manifest.json")
schedule = load_json(ROOT / "meeting_schedule.json")
seat_map = load_seat_map(ROOT / "room_seat_map.csv")
checkins = load_checkins(ROOT / "checkin_log.csv")

shape = [len(seat_map), len(seat_map[0])]
if shape != manifest["seat_matrix_shape"]:
    raise ValueError("seat map shape does not match manifest")

empty_token = manifest["empty_seat_token"]
seat_positions = {}
for row_idx, row in enumerate(seat_map):
    if len(row) != shape[1]:
        raise ValueError("seat map rows must have equal length")
    for col_idx, cell in enumerate(row):
        if cell != empty_token:
            if cell in seat_positions:
                raise ValueError(f"duplicate seat id: {cell}")
            seat_positions[cell] = (row_idx, col_idx)

meeting_by_slot = {}
for item in schedule:
    start = int(item["start_slot"])
    end = int(item["end_slot"])
    if not (0 <= start < end <= int(manifest["slot_count"])):
        raise ValueError(f"invalid meeting range for {item['meeting_id']}")
    for slot_idx in range(start, end):
        if slot_idx in meeting_by_slot:
            raise ValueError("meeting schedule overlaps")
        meeting_by_slot[slot_idx] = item

timeline = []
npz_payload = {
    "shape": np.asarray(manifest["seat_matrix_shape"], dtype=np.int64),
    "slots": np.arange(int(manifest["slot_count"]), dtype=np.int64),
}

for slot_idx in range(int(manifest["slot_count"])):
    active_meeting = meeting_by_slot.get(slot_idx)
    occupied_seat_ids = sorted(
        row["seat_id"]
        for row in checkins
        if row["slot_start"] <= slot_idx < row["slot_end"]
    )

    dense = np.zeros(tuple(shape), dtype=bool)
    for seat_id in occupied_seat_ids:
        if seat_id not in seat_positions:
            raise ValueError(f"unknown seat id: {seat_id}")
        row_idx, col_idx = seat_positions[seat_id]
        dense[row_idx, col_idx] = True

    occupied_count = len(occupied_seat_ids)
    if active_meeting is None:
        state = "Vacant" if occupied_count == 0 else "Reset"
        meeting_id = None
        meeting_title = None
    else:
        reserved = int(active_meeting["reserved_seats"])
        if occupied_count > reserved:
            state = "Overflow"
        elif slot_idx == int(active_meeting["start_slot"]) or occupied_count < reserved:
            state = "Check-In"
        else:
            state = "In Session"
        meeting_id = active_meeting["meeting_id"]
        meeting_title = active_meeting["title"]

    timeline.append(
        {
            "slot_idx": slot_idx,
            "window": manifest["slot_windows"][slot_idx],
            "state": state,
            "meeting_id": meeting_id,
            "meeting_title": meeting_title,
            "occupied_count": occupied_count,
            "occupied_seat_ids": occupied_seat_ids,
        }
    )

    data, indices, indptr = build_csr(dense)
    npz_payload[f"slot_{slot_idx}_data"] = data
    npz_payload[f"slot_{slot_idx}_indices"] = indices
    npz_payload[f"slot_{slot_idx}_indptr"] = indptr

output = {
    "room_id": manifest["room_id"],
    "seat_matrix_shape": manifest["seat_matrix_shape"],
    "seat_matrix_path": manifest["seat_matrix_path"],
    "timeline": timeline,
}

with (ROOT / "room_state_timeline.json").open("w", encoding="utf-8") as fh:
    json.dump(output, fh, ensure_ascii=False, indent=2)

np.savez(ROOT / "seat_usage_csr.npz", **npz_payload)
PY
