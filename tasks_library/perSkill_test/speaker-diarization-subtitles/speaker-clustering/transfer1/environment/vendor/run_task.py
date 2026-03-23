from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from cluster_utils import (
    cluster_records,
    load_records,
    merge_adjacent,
    speaker_durations,
    to_rttm_label,
)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    ensure_parent(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def format_number(value: float) -> str:
    return f"{value:.2f}"


def build_rttm_and_report(records: list[dict], labels: list[str], config: dict) -> None:
    merged = merge_adjacent(records, labels, config["merge_gap_sec"])
    output_path = Path(config["outputs"]["rttm"])
    ensure_parent(output_path)
    lines = []
    for item in merged:
        speaker_name = to_rttm_label(item["speaker_label"])
        lines.append(
            "SPEAKER {file_id} 1 {start:.6f} {duration:.6f} <NA> <NA> {speaker} <NA> <NA>".format(
                file_id=config["rttm_file_id"],
                start=item["start_sec"],
                duration=item["duration_sec"],
                speaker=speaker_name,
            )
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    totals = {}
    for key, value in speaker_durations(labels, records).items():
        totals[to_rttm_label(key)] = value
    report = {
        "merged_turn_count": len(merged),
        "segment_count": len(records),
        "speaker_count": len(set(labels)),
        "speaker_durations_sec": totals,
    }
    write_json(Path(config["outputs"]["report"]), report)


def build_manifest(records: list[dict], labels: list[str], config: dict) -> None:
    rows = []
    for record, label in zip(records, labels):
        rows.append(
            {
                "segment_id": record["segment_id"],
                "zone": record["zone"],
                "start_sec": format_number(record["start_sec"]),
                "end_sec": format_number(record["end_sec"]),
                "duration_sec": format_number(record["duration_sec"]),
                "speaker_label": label,
            }
        )
    write_csv(
        Path(config["outputs"]["manifest"]),
        rows,
        ["segment_id", "zone", "start_sec", "end_sec", "duration_sec", "speaker_label"],
    )
    summary = {
        "durations_sec": speaker_durations(labels, records),
        "segments_per_speaker": {
            label: sum(1 for current in labels if current == label) for label in sorted(set(labels))
        },
        "speaker_count": len(set(labels)),
    }
    write_json(Path(config["outputs"]["summary"]), summary)


def build_rollup(records: list[dict], labels: list[str], config: dict) -> None:
    buckets = []
    for label in sorted(set(labels)):
        selected = [record for record, current_label in zip(records, labels) if current_label == label]
        buckets.append(
            {
                "first_seen_sec": round(selected[0]["start_sec"], 2),
                "seats": sorted({record["seat"] for record in selected}),
                "segment_ids": [record["segment_id"] for record in selected],
                "speaker_label": label,
                "total_duration_sec": round(sum(record["duration_sec"] for record in selected), 2),
            }
        )
    payload = {
        "buckets": buckets,
        "speaker_count": len(buckets),
        "total_duration_sec": round(sum(record["duration_sec"] for record in records), 2),
    }
    write_json(Path(config["outputs"]["rollup"]), payload)


def build_markdown(records: list[dict], labels: list[str], config: dict) -> None:
    merged = merge_adjacent(records, labels, config["merge_gap_sec"])
    speaker_order = []
    for item in merged:
        if item["speaker_label"] not in speaker_order:
            speaker_order.append(item["speaker_label"])

    lines = ["# Transfer 3 Session Brief", "", f"Speaker count: {len(set(labels))}", f"Merged turns: {len(merged)}", ""]
    for label in speaker_order:
        label_turns = [item for item in merged if item["speaker_label"] == label]
        total_duration = round(sum(item["duration_sec"] for item in label_turns), 2)
        lines.append(f"## {label}")
        lines.append(f"Total duration (sec): {total_duration:.2f}")
        lines.append("Turns:")
        for item in label_turns:
            lines.append(f"- {item['start_sec']:.2f}-{item['end_sec']:.2f}")
        lines.append("")

    output_path = Path(config["outputs"]["brief"])
    ensure_parent(output_path)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    config_path = Path(sys.argv[1])
    config = json.loads(config_path.read_text())
    records = load_records(config)
    labels = cluster_records(records, config)

    output_type = config["output_type"]
    if output_type == "rttm_report":
        build_rttm_and_report(records, labels, config)
        return
    if output_type == "manifest_csv":
        build_manifest(records, labels, config)
        return
    if output_type == "rollup_json":
        build_rollup(records, labels, config)
        return
    if output_type == "markdown_brief":
        build_markdown(records, labels, config)
        return
    raise ValueError(f"Unsupported output_type: {output_type}")


if __name__ == "__main__":
    main()
