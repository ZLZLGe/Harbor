#!/bin/bash

set -euo pipefail

mkdir -p /app/artifacts

python3 - <<'PY'
import json
import re
import zlib
from collections import defaultdict
from pathlib import Path


def decode_hex(hex_string: str) -> str:
    chars = []
    for i in range(0, len(hex_string), 4):
        code = int(hex_string[i:i + 4], 16)
        if code == 0:
            continue
        if code <= 0xFF:
            chars.append(chr(code + 29))
    return "".join(chars)


def extract_pdf_text(pdf_path: Path) -> str:
    raw = pdf_path.read_bytes()
    pages = []
    for match in re.finditer(rb"stream\r?\n", raw):
        start = match.end()
        end = raw.find(b"endstream", start)
        if end == -1:
            continue
        stream = raw[start:end]
        if stream.endswith(b"\r\n"):
            stream = stream[:-2]
        elif stream.endswith(b"\n"):
            stream = stream[:-1]
        try:
            decoded = zlib.decompress(stream).decode("latin1", "ignore")
        except Exception:
            continue
        if "BT" not in decoded or "Tm" not in decoded or "Tj" not in decoded:
            continue

        entries = []
        current_x = None
        current_y = None
        for line in decoded.splitlines():
            line = line.strip()
            tm_match = re.search(r"1 0 0 -1 ([0-9.]+) ([0-9.]+) Tm", line)
            if tm_match:
                current_x = float(tm_match.group(1))
                current_y = float(tm_match.group(2))
                continue
            tj_match = re.search(r"<([0-9A-Fa-f]+)> Tj", line)
            if tj_match and current_x is not None and current_y is not None:
                entries.append((round(current_y), current_x, decode_hex(tj_match.group(1))))

        if not entries:
            continue

        lines = defaultdict(list)
        for y_value, x_value, text in entries:
            lines[y_value].append((x_value, text))

        page_lines = []
        for y_value in sorted(lines):
            text = "".join(part for _, part in sorted(lines[y_value])).strip()
            if text:
                page_lines.append(text)
        if page_lines:
            pages.append("\n".join(page_lines))

    return "\n".join(pages)


pdf_path = Path("/app/workspace/input/cluster_schema.pdf")
text = extract_pdf_text(pdf_path)

for phrase in [
    "Google cluster-usage traces: format +",
    "Time and timestamps",
    "Job events table",
    "Task events table",
    "SUBMIT (0)",
    "microseconds",
]:
    if phrase not in text:
        raise SystemExit(f"Expected phrase not found in PDF extraction: {phrase}")

output = {
    "source_document": "input/cluster_schema.pdf",
    "document_title": "Google cluster-usage traces: format + schema",
    "time_semantics": {
        "unit": "microseconds",
        "base_reference": "Timestamps are in microseconds since 600 seconds before the beginning of the trace period.",
        "usage_measurement_precision": "Usage measurements have best available precision to the nearest second.",
        "usage_measurement_reporting": "Usage measurements are still reported in microseconds for consistency.",
        "special_values": [
            {
                "value": "0",
                "meaning": "Represents events that occurred before the trace window.",
            },
            {
                "value": "2^63-1",
                "meaning": "Represents events that occur after the end of the trace window.",
            },
        ],
    },
    "event_type_codes": [
        {
            "code": 0,
            "name": "SUBMIT",
            "meaning": "A task or job became eligible for scheduling.",
        },
        {
            "code": 1,
            "name": "SCHEDULE",
            "meaning": "A task or job was scheduled on a machine; for jobs this is the first time any task of the job is scheduled.",
        },
        {
            "code": 2,
            "name": "EVICT",
            "meaning": "A task or job was descheduled because of higher priority work, overcommit, an unusable machine, or lost task data.",
        },
        {
            "code": 3,
            "name": "FAIL",
            "meaning": "A task or job was descheduled or ceased to be eligible because of task failure.",
        },
        {
            "code": 4,
            "name": "FINISH",
            "meaning": "A task or job completed normally.",
        },
        {
            "code": 5,
            "name": "KILL",
            "meaning": "A task or job was cancelled by a user, a driver program, or a dependency failure.",
        },
        {
            "code": 6,
            "name": "LOST",
            "meaning": "A task or job was presumed terminated because the termination record was missing from the source data.",
        },
        {
            "code": 7,
            "name": "UPDATE_PENDING",
            "meaning": "Scheduling class, resource requirements, or constraints were updated while the task or job was waiting to be scheduled.",
        },
        {
            "code": 8,
            "name": "UPDATE_RUNNING",
            "meaning": "Scheduling class, resource requirements, or constraints were updated while the task or job was already scheduled.",
        },
    ],
    "job_events": {
        "field_count": 8,
        "fields": [
            {"position": 1, "name": "timestamp", "meaning": "Event timestamp in microseconds."},
            {
                "position": 2,
                "name": "missing_info",
                "meaning": "Reason code for synthesized records; empty when the record is not synthesized.",
            },
            {"position": 3, "name": "job_id", "meaning": "Unique 64-bit identifier for the job."},
            {"position": 4, "name": "event_type", "meaning": "Lifecycle transition code for the job event."},
            {
                "position": 5,
                "name": "user_name",
                "meaning": "Opaque base64-encoded hash of the submitting user or service.",
            },
            {
                "position": 6,
                "name": "scheduling_class",
                "meaning": "Latency-sensitivity class where 3 is more latency-sensitive and 0 is non-production.",
            },
            {"position": 7, "name": "job_name", "meaning": "Opaque hashed job name."},
            {
                "position": 8,
                "name": "logical_job_name",
                "meaning": "Opaque normalized job name that usually groups runs of the same program.",
            },
        ],
    },
    "task_events": {
        "field_count": 13,
        "fields": [
            {"position": 1, "name": "timestamp", "meaning": "Event timestamp in microseconds."},
            {
                "position": 2,
                "name": "missing_info",
                "meaning": "Reason code for synthesized records; empty when the record is not synthesized.",
            },
            {"position": 3, "name": "job_id", "meaning": "Unique 64-bit identifier of the parent job."},
            {"position": 4, "name": "task_index", "meaning": "0-based task index within the job."},
            {
                "position": 5,
                "name": "machine_id",
                "meaning": "Machine onto which the task was scheduled when a machine is present.",
            },
            {"position": 6, "name": "event_type", "meaning": "Lifecycle transition code for the task event."},
            {
                "position": 7,
                "name": "user_name",
                "meaning": "Opaque base64-encoded hash of the submitting user or service.",
            },
            {
                "position": 8,
                "name": "scheduling_class",
                "meaning": "Latency-sensitivity class where 3 is more latency-sensitive and 0 is non-production.",
            },
            {
                "position": 9,
                "name": "priority",
                "meaning": "Sorted-set priority where larger numbers are generally more important.",
            },
            {
                "position": 10,
                "name": "cpu_request",
                "meaning": "Maximum CPU cores the task is permitted to use.",
            },
            {
                "position": 11,
                "name": "ram_request",
                "meaning": "Maximum RAM the task is permitted to use.",
            },
            {
                "position": 12,
                "name": "local_disk_space_request",
                "meaning": "Maximum local disk space the task is permitted to use.",
            },
            {
                "position": 13,
                "name": "different_machine_constraint",
                "meaning": "Boolean indicating the task must run on a different machine than other running tasks in the same job.",
            },
        ],
    },
}

Path("/app/artifacts/cluster_event_schema.json").write_text(
    json.dumps(output, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
PY
