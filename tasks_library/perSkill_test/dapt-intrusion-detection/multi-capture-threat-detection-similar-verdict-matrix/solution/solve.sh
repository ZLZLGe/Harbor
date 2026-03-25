#!/bin/bash

set -euo pipefail

python3 <<'PY'
import json

INPUT_PATH = "/root/capture_feature_matrix.json"
OUTPUT_PATH = "/root/capture_verdicts.json"


def detect_port_scan(record):
    return (
        record["port_entropy"] > 6.0
        and record["syn_only_ratio"] > 0.7
        and record["unique_ports"] > 100
    )


def detect_dos_pattern(record):
    avg = record["packets_per_minute_avg"]
    if avg == 0:
        return False
    return (record["packets_per_minute_max"] / avg) > 20


def detect_beaconing(record):
    return record["iat_cv"] < 0.5


def dominant_risk(has_port_scan, has_dos_pattern, has_beaconing):
    active = [
        name
        for name, enabled in (
            ("port_scan", has_port_scan),
            ("dos_pattern", has_dos_pattern),
            ("beaconing", has_beaconing),
        )
        if enabled
    ]
    if not active:
        return "benign"
    if len(active) == 1:
        return active[0]
    return "multi_threat"


with open(INPUT_PATH, "r", encoding="utf-8") as infile:
    captures = json.load(infile)

verdicts = []
for capture in captures:
    has_port_scan = detect_port_scan(capture)
    has_dos_pattern = detect_dos_pattern(capture)
    has_beaconing = detect_beaconing(capture)
    is_traffic_benign = not (has_port_scan or has_dos_pattern or has_beaconing)

    verdicts.append(
        {
            "capture_id": capture["capture_id"],
            "has_port_scan": has_port_scan,
            "has_dos_pattern": has_dos_pattern,
            "has_beaconing": has_beaconing,
            "is_traffic_benign": is_traffic_benign,
            "dominant_risk": dominant_risk(
                has_port_scan, has_dos_pattern, has_beaconing
            ),
        }
    )

with open(OUTPUT_PATH, "w", encoding="utf-8") as outfile:
    json.dump(verdicts, outfile, indent=2)
    outfile.write("\n")
PY
