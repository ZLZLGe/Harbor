from __future__ import annotations

import csv
import json
from pathlib import Path


def round3(value: float) -> float:
    return round(float(value) + 1e-9, 3)


def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_csv_rows(path: str | Path, delimiter: str = ",") -> list[dict]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def clean_segments(
    raw_segments: list[dict], gap_threshold: float = 0.25, min_duration: float = 0.30
) -> list[dict]:
    normalized = []
    for row in raw_segments:
        start = float(row["start"])
        end = float(row["end"])
        if end <= start:
            continue
        normalized.append(
            {
                "id": row.get("id", ""),
                "start": round3(start),
                "end": round3(end),
            }
        )

    normalized.sort(key=lambda item: (item["start"], item["end"], item["id"]))

    merged: list[dict] = []
    for row in normalized:
        if not merged:
            merged.append(
                {"start": row["start"], "end": row["end"], "source_ids": [row["id"]]}
            )
            continue

        previous = merged[-1]
        if row["start"] - previous["end"] <= gap_threshold + 1e-9:
            previous["end"] = max(previous["end"], row["end"])
            if row["id"]:
                previous["source_ids"].append(row["id"])
        else:
            merged.append(
                {"start": row["start"], "end": row["end"], "source_ids": [row["id"]]}
            )

    kept: list[dict] = []
    for merged_row in merged:
        duration = round3(merged_row["end"] - merged_row["start"])
        if duration + 1e-9 < min_duration:
            continue
        kept.append(
            {
                "segment_id": f"speech_{len(kept) + 1:02d}",
                "start_sec": round3(merged_row["start"]),
                "end_sec": round3(merged_row["end"]),
                "duration_sec": duration,
                "source_ids": [item for item in merged_row["source_ids"] if item],
            }
        )

    return kept


def compute_silence_windows(
    speech_segments: list[dict],
    region_start: float,
    region_end: float,
    min_duration: float,
) -> list[dict]:
    silence_rows: list[dict] = []
    cursor = round3(region_start)
    left_context = "START"
    for segment in speech_segments:
        start = float(segment["start_sec"])
        end = float(segment["end_sec"])
        if start - cursor >= min_duration - 1e-9:
            silence_rows.append(
                {
                    "silence_id": f"silence_{len(silence_rows) + 1:02d}",
                    "start_sec": round3(cursor),
                    "end_sec": round3(start),
                    "duration_sec": round3(start - cursor),
                    "left_context": left_context,
                    "right_context": segment["segment_id"],
                }
            )
        cursor = end
        left_context = segment["segment_id"]

    if region_end - cursor >= min_duration - 1e-9:
        silence_rows.append(
            {
                "silence_id": f"silence_{len(silence_rows) + 1:02d}",
                "start_sec": round3(cursor),
                "end_sec": round3(region_end),
                "duration_sec": round3(region_end - cursor),
                "left_context": left_context,
                "right_context": "END",
            }
        )
    return silence_rows
