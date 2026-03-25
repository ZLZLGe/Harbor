#!/bin/bash

set -euo pipefail

python3 <<'PY'
import csv
from collections import defaultdict

INPUT_FILE = "/root/branch_vpn_hourly_features.csv"
OUTPUT_FILE = "/root/branch_soc_report.md"
THREAT_ORDER = ("port_scan", "dos_pattern", "beaconing")


def bool_flags(row):
    has_port_scan = (
        float(row["port_entropy"]) > 6.0
        and float(row["syn_only_ratio"]) > 0.7
        and int(row["unique_destination_ports"]) > 100
    )

    avg = float(row["packets_per_minute_avg"])
    has_dos = False if avg == 0 else (float(row["packets_per_minute_max"]) / avg) > 20
    has_beacon = float(row["iat_cv"]) < 0.5
    return {
        "port_scan": has_port_scan,
        "dos_pattern": has_dos,
        "beaconing": has_beacon,
    }


def dos_ratio(row):
    avg = float(row["packets_per_minute_avg"])
    if avg == 0:
        return 0.0
    return float(row["packets_per_minute_max"]) / avg


def evidence_line(threat, row):
    if threat == "port_scan":
        return (
            f'- port_scan evidence: {row["hour_utc"]} | '
            f'port_entropy={row["port_entropy"]} (> 6.0), '
            f'syn_only_ratio={row["syn_only_ratio"]} (> 0.7), '
            f'unique_destination_ports={row["unique_destination_ports"]} (> 100)'
        )
    if threat == "dos_pattern":
        ratio = dos_ratio(row)
        return (
            f'- dos_pattern evidence: {row["hour_utc"]} | '
            f'packets_per_minute_max/avg={ratio:.2f} using '
            f'{row["packets_per_minute_max"]}/{row["packets_per_minute_avg"]} (> 20)'
        )
    return (
        f'- beaconing evidence: {row["hour_utc"]} | '
        f'iat_cv={row["iat_cv"]} (< 0.5)'
    )


with open(INPUT_FILE, "r", encoding="utf-8", newline="") as infile:
    rows = list(csv.DictReader(infile))

sites = defaultdict(list)
for row in rows:
    row["flags"] = bool_flags(row)
    sites[row["site_code"]].append(row)

escalated = []
for site_code, site_rows in sites.items():
    region = site_rows[0]["region"]
    triggered = [
        threat
        for threat in THREAT_ORDER
        if any(row["flags"][threat] for row in site_rows)
    ]
    if not triggered:
        continue

    evidence = {}
    for threat in triggered:
        matched = [row for row in site_rows if row["flags"][threat]]
        if threat == "port_scan":
            matched.sort(key=lambda row: (-float(row["port_entropy"]), row["hour_utc"]))
        elif threat == "dos_pattern":
            matched.sort(key=lambda row: (-dos_ratio(row), row["hour_utc"]))
        else:
            matched.sort(key=lambda row: (float(row["iat_cv"]), row["hour_utc"]))
        evidence[threat] = matched[0]

    escalated.append(
        {
            "site_code": site_code,
            "region": region,
            "triggered": triggered,
            "evidence": evidence,
        }
    )

escalated.sort(key=lambda item: item["site_code"])

summary = {
    "total_sites": len(sites),
    "escalated_sites": len(escalated),
    "port_scan": sum(1 for item in escalated if "port_scan" in item["triggered"]),
    "dos_pattern": sum(1 for item in escalated if "dos_pattern" in item["triggered"]),
    "beaconing": sum(1 for item in escalated if "beaconing" in item["triggered"]),
}

lines = [
    "# Branch VPN SOC Brief",
    "",
    "## Global Summary",
    f'- Total sites analyzed: {summary["total_sites"]}',
    f'- Sites requiring escalation: {summary["escalated_sites"]}',
    f'- Sites with port_scan evidence: {summary["port_scan"]}',
    f'- Sites with dos_pattern evidence: {summary["dos_pattern"]}',
    f'- Sites with beaconing evidence: {summary["beaconing"]}',
    "",
    "## Escalated Sites",
]

if not escalated:
    lines.append("No sites require escalation.")
else:
    for item in escalated:
        lines.extend(
            [
                "",
                f'### {item["site_code"]} ({item["region"]})',
                f'- Triggered threats: {", ".join(item["triggered"])}',
            ]
        )
        for threat in item["triggered"]:
            lines.append(evidence_line(threat, item["evidence"][threat]))

with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
    outfile.write("\n".join(lines) + "\n")
PY
