from __future__ import annotations

import csv
import json
from pathlib import Path


def round3(value: float) -> float:
    return round(float(value) + 1e-9, 3)


def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_csv_rows(path: str | Path, delimiter: str = "\t") -> list[dict]:
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


def build_padded_cues(
    speech_segments: list[dict], pre_roll: float, post_roll: float, clip_end: float
) -> list[dict]:
    expanded = []
    for segment in speech_segments:
        expanded.append(
            {
                "start": round3(max(0.0, float(segment["start_sec"]) - pre_roll)),
                "end": round3(min(clip_end, float(segment["end_sec"]) + post_roll)),
                "source_segments": [segment["segment_id"]],
            }
        )

    merged: list[dict] = []
    for row in expanded:
        if not merged:
            merged.append(row)
            continue
        previous = merged[-1]
        if row["start"] <= previous["end"] + 1e-9:
            previous["end"] = round3(max(previous["end"], row["end"]))
            previous["source_segments"].extend(row["source_segments"])
        else:
            merged.append(row)

    cues = []
    for index, row in enumerate(merged, start=1):
        cues.append(
            {
                "cue_id": f"cue_{index:02d}",
                "start_sec": round3(row["start"]),
                "end_sec": round3(row["end"]),
                "duration_sec": round3(row["end"] - row["start"]),
                "source_segment_count": len(row["source_segments"]),
                "source_segments": row["source_segments"],
            }
        )
    return cues
