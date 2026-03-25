#!/bin/bash

set -euo pipefail

python3 <<'PY'
import csv

INPUT_FILE = "/root/gateway_tenant_profiles.tsv"
OUTPUT_FILE = "/root/gateway_escalations.csv"
THREAT_ORDER = ("port_scan", "dos_pattern", "beaconing")
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def detect_flags(row):
    port_scan = (
        float(row["dst_port_entropy"]) > 6.0
        and float(row["syn_probe_ratio"]) > 0.7
        and int(row["distinct_external_ports"]) > 100
    )
    baseline = float(row["rpm_baseline"])
    dos_pattern = False if baseline == 0 else (float(row["rpm_peak"]) / baseline) > 20
    beaconing = float(row["checkin_iat_cv"]) < 0.5
    return {
        "port_scan": port_scan,
        "dos_pattern": dos_pattern,
        "beaconing": beaconing,
    }


def threat_labels(flags):
    active = [name for name in THREAT_ORDER if flags[name]]
    return ";".join(active) if active else "benign"


def priority_for(flags):
    if flags["port_scan"] and flags["dos_pattern"]:
        return "critical"
    if flags["port_scan"] or (flags["dos_pattern"] and flags["beaconing"]):
        return "high"
    if flags["dos_pattern"] or flags["beaconing"]:
        return "medium"
    return "low"


def queue_for(flags):
    if flags["port_scan"]:
        return "tenant-abuse"
    if flags["dos_pattern"]:
        return "traffic-surge"
    if flags["beaconing"]:
        return "signal-review"
    return "baseline-monitoring"


rows = []
with open(INPUT_FILE, "r", encoding="utf-8", newline="") as infile:
    reader = csv.DictReader(infile, delimiter="\t")
    for row in reader:
        flags = detect_flags(row)
        rows.append(
            {
                "tenant_id": row["tenant_id"],
                "threat_labels": threat_labels(flags),
                "priority": priority_for(flags),
                "dispatch_queue": queue_for(flags),
            }
        )

rows.sort(key=lambda row: (PRIORITY_ORDER[row["priority"]], row["tenant_id"]))

with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as outfile:
    writer = csv.DictWriter(
        outfile,
        fieldnames=["tenant_id", "threat_labels", "priority", "dispatch_queue"],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
