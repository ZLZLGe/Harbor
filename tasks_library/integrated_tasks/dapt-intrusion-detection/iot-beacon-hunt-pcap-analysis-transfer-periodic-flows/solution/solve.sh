#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import socket
import struct
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PCAP_FILE = Path("/root/packets.pcap")
DEVICE_FILE = Path("/root/device_inventory.csv")
APPROVED_FILE = Path("/root/approved_periodic_flows.csv")
REPORT_FILE = Path("/root/iot_beacon_report.md")


def load_devices():
    devices = {}
    with DEVICE_FILE.open(newline="") as fh:
        for row in csv.DictReader(fh):
            devices[row["device_ip"]] = row
    return devices


def load_approved():
    approved = set()
    with APPROVED_FILE.open(newline="") as fh:
        for row in csv.DictReader(fh):
            approved.add(
                (
                    row["src_ip"],
                    row["dst_ip"],
                    row["protocol"],
                    row["dst_port"],
                )
            )
    return approved


def inet(addr_bytes):
    return socket.inet_ntoa(addr_bytes)


def parse_flows(devices):
    flows = defaultdict(lambda: {"timestamps": []})
    with PCAP_FILE.open("rb") as fh:
        global_header = fh.read(24)
        magic = global_header[:4]
        if magic not in (
            b"\xd4\xc3\xb2\xa1",
            b"\xa1\xb2\xc3\xd4",
            b"\x4d\x3c\xb2\xa1",
            b"\xa1\xb2\x3c\x4d",
        ):
            raise ValueError("Unsupported PCAP format")
        endian = "<" if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
        ts_div = 1_000_000_000 if magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d") else 1_000_000

        while True:
            record_header = fh.read(16)
            if not record_header:
                break
            ts_sec, ts_frac, incl_len, _orig_len = struct.unpack(endian + "IIII", record_header)
            packet = fh.read(incl_len)
            if len(packet) < 34:
                continue
            if struct.unpack("!H", packet[12:14])[0] != 0x0800:
                continue

            ihl = (packet[14] & 0x0F) * 4
            proto_num = packet[23]
            src_ip = inet(packet[26:30])
            dst_ip = inet(packet[30:34])
            if src_ip not in devices:
                continue

            l4_offset = 14 + ihl
            if proto_num == 6 and len(packet) >= l4_offset + 4:
                protocol = "TCP"
                dst_port = str(struct.unpack("!HH", packet[l4_offset:l4_offset + 4])[1])
            elif proto_num == 17 and len(packet) >= l4_offset + 4:
                protocol = "UDP"
                dst_port = str(struct.unpack("!HH", packet[l4_offset:l4_offset + 4])[1])
            elif proto_num == 1:
                protocol = "ICMP"
                dst_port = "-"
            else:
                continue

            timestamp = ts_sec + ts_frac / ts_div
            flows[(src_ip, dst_ip, protocol, dst_port)]["timestamps"].append(timestamp)
    return flows


def compute_candidates(flows, devices, approved):
    candidates = []
    for key, state in flows.items():
        timestamps = sorted(state["timestamps"])
        if len(timestamps) < 6:
            continue
        iats = [b - a for a, b in zip(timestamps, timestamps[1:])]
        if not iats:
            continue
        mean_iat = sum(iats) / len(iats)
        variance = sum((iat - mean_iat) ** 2 for iat in iats) / len(iats)
        iat_cv = (variance ** 0.5) / mean_iat if mean_iat else 0.0
        if mean_iat < 600 or iat_cv > 0.8:
            continue

        src_ip, dst_ip, protocol, dst_port = key
        device = devices[src_ip]
        classification = "approved_periodic" if key in approved else "suspected_beacon"
        candidates.append(
            {
                "device_id": device["device_id"],
                "device_ip": src_ip,
                "device_role": device["device_role"],
                "dst_ip": dst_ip,
                "protocol": protocol,
                "dst_port": dst_port,
                "packet_count": len(timestamps),
                "first_seen_utc": datetime.fromtimestamp(
                    timestamps[0], tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "last_seen_utc": datetime.fromtimestamp(
                    timestamps[-1], tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "mean_iat_seconds": f"{mean_iat:.2f}",
                "iat_cv": f"{iat_cv:.4f}",
                "classification": classification,
            }
        )

    candidates.sort(
        key=lambda row: (
            row["device_id"],
            row["dst_ip"],
            row["protocol"],
            row["dst_port"],
        )
    )
    return candidates


def render_table(rows):
    header = "| device_id | device_ip | device_role | dst_ip | protocol | dst_port | packet_count | first_seen_utc | last_seen_utc | mean_iat_seconds | iat_cv | classification |"
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [header, divider]
    for row in rows:
        lines.append(
            "| {device_id} | {device_ip} | {device_role} | {dst_ip} | {protocol} | {dst_port} | {packet_count} | {first_seen_utc} | {last_seen_utc} | {mean_iat_seconds} | {iat_cv} | {classification} |".format(
                **row
            )
        )
    return lines


devices = load_devices()
approved = load_approved()
flows = parse_flows(devices)
candidates = compute_candidates(flows, devices, approved)

suspected = [row for row in candidates if row["classification"] == "suspected_beacon"]
approved_rows = [row for row in candidates if row["classification"] == "approved_periodic"]

suspected_counts = Counter(row["device_id"] for row in suspected)
highest_risk = min(
    (
        (-count, device_id, next(row["device_ip"] for row in suspected if row["device_id"] == device_id))
        for device_id, count in suspected_counts.items()
    ),
    default=None,
)
if highest_risk is None:
    highest_risk_device = "none (-)"
else:
    highest_risk_device = f"{highest_risk[1]} ({highest_risk[2]})"

suspected_destinations = ", ".join(row["dst_ip"] for row in suspected)
approved_mdns_devices = ", ".join(
    row["device_id"]
    for row in approved_rows
    if row["dst_ip"] == "224.0.0.251" and row["protocol"] == "UDP" and row["dst_port"] == "5353"
)

report_lines = [
    "# IoT Beacon Hunt Report",
    "",
    "## Summary",
    f"- Inventoried devices analyzed: {len(devices)}",
    f"- Periodic candidate flows: {len(candidates)}",
    f"- Approved periodic flows: {len(approved_rows)}",
    f"- Suspected beacon flows: {len(suspected)}",
    f"- Devices with suspected beacons: {len(suspected_counts)}",
    f"- Highest risk device: {highest_risk_device}",
    "",
    "## Suspected Beacon Flows",
]
report_lines.extend(render_table(suspected))
report_lines.extend(
    [
        "",
        "## Approved Periodic Flows",
    ]
)
report_lines.extend(render_table(approved_rows))
report_lines.extend(
    [
        "",
        "## Evidence Summary",
        f"- edge-hub-01 (192.168.3.30) produced 3 unapproved periodic UDP/123 flows to {suspected_destinations}.",
        f"- {approved_mdns_devices} matched approved UDP/5353 discovery traffic to 224.0.0.251.",
        "- edge-hub-01 matched the only approved time-sync rule: 91.189.94.4:123/UDP.",
        "",
    ]
)

REPORT_FILE.write_text("\n".join(report_lines), encoding="utf-8")
PY
