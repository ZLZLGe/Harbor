#!/bin/bash

set -euo pipefail

python3 <<'PY'
import csv
import json
from pathlib import Path

WORKBOOK_DIR = Path("/root/campus_feature_workbook")
OUTPUT_FILE = Path("/root/campus_verdict.json")


def load_overview(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values[row["metric"]] = row["value"]
    return values


def load_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


overview = load_overview(WORKBOOK_DIR / "traffic_overview.csv")
candidates = load_candidates(WORKBOOK_DIR / "scan_candidates.csv")

ppm_avg = float(overview["packets_per_minute_avg"])
ppm_max = int(float(overview["packets_per_minute_max"]))
iat_cv = float(overview["iat_cv"])
dos_ratio = ppm_max / ppm_avg if ppm_avg else 0.0

port_scan_candidate = None
for row in candidates:
    total_tcp_packets = int(row["total_tcp_packets"])
    unique_dst_ports = int(row["unique_dst_ports"])
    dst_port_entropy = float(row["dst_port_entropy"])
    syn_only_ratio = float(row["syn_only_ratio"])

    if (
        total_tcp_packets >= 50
        and unique_dst_ports > 100
        and dst_port_entropy > 6.0
        and syn_only_ratio > 0.7
    ):
        port_scan_candidate = {
            "source_ip": row["source_ip"],
            "unique_dst_ports": unique_dst_ports,
            "dst_port_entropy": dst_port_entropy,
            "syn_only_ratio": syn_only_ratio,
        }
        break

has_port_scan = port_scan_candidate is not None
has_dos_pattern = dos_ratio > 20
has_beaconing = iat_cv < 0.5
is_traffic_benign = not (has_port_scan or has_dos_pattern or has_beaconing)

result = {
    "capture_id": overview["capture_id"],
    "verdict": "benign" if is_traffic_benign else "malicious",
    "is_traffic_benign": is_traffic_benign,
    "has_port_scan": has_port_scan,
    "has_dos_pattern": has_dos_pattern,
    "has_beaconing": has_beaconing,
    "supporting_metrics": {
        "port_scan_source": port_scan_candidate["source_ip"] if port_scan_candidate else None,
        "port_scan_unique_ports": port_scan_candidate["unique_dst_ports"] if port_scan_candidate else 0,
        "port_scan_dst_port_entropy": port_scan_candidate["dst_port_entropy"] if port_scan_candidate else 0.0,
        "port_scan_syn_only_ratio": port_scan_candidate["syn_only_ratio"] if port_scan_candidate else 0.0,
        "packets_per_minute_avg": ppm_avg,
        "packets_per_minute_max": ppm_max,
        "dos_ratio": round(dos_ratio, 3),
        "iat_cv": iat_cv,
    },
}

OUTPUT_FILE.write_text(json.dumps(result, indent=2) + "\n")
PY
