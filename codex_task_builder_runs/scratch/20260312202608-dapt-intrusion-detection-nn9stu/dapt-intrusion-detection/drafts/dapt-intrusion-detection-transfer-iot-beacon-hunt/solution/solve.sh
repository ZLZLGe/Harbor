#!/bin/bash

set -euo pipefail

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INPUT_PCAP="${INPUT_PCAP:-/root/iot_building_capture.pcap}"
INVENTORY_FILE="${INVENTORY_FILE:-/root/iot_device_inventory.json}"
OUTPUT_FILE="${OUTPUT_FILE:-${PRIMARY_OUTPUT_FILE:-/root/iot_beacon_findings.json}}"

if [ ! -f "$INPUT_PCAP" ]; then
  INPUT_PCAP="$TASK_ROOT/environment/iot_building_capture.pcap"
fi

if [ ! -f "$INVENTORY_FILE" ]; then
  INVENTORY_FILE="$TASK_ROOT/environment/iot_device_inventory.json"
fi

if [ ! -d "$(dirname "$OUTPUT_FILE")" ] || [ ! -w "$(dirname "$OUTPUT_FILE")" ]; then
  OUTPUT_FILE="$TASK_ROOT/.tmp_iot_beacon_findings.json"
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"

INPUT_PCAP="$INPUT_PCAP" INVENTORY_FILE="$INVENTORY_FILE" OUTPUT_FILE="$OUTPUT_FILE" python3 <<'PY'
import ipaddress
import json
import math
import os
import struct
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


INPUT_PCAP = Path(os.environ["INPUT_PCAP"])
INVENTORY_FILE = Path(os.environ["INVENTORY_FILE"])
OUTPUT_FILE = Path(os.environ["OUTPUT_FILE"])


def format_mac(raw):
    return ":".join(f"{byte:02x}" for byte in raw)


def format_ip(raw):
    return ".".join(str(byte) for byte in raw)


def shannon_entropy(counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        if count <= 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def round4(value):
    return round(float(value), 4)


def load_inventory(path):
    data = json.loads(path.read_text())
    by_ip = {}
    for item in data:
        by_ip[item["ip"]] = item
    return by_ip


def parse_pcap(path):
    packets = []
    with path.open("rb") as handle:
        global_header = handle.read(24)
        if len(global_header) != 24:
            raise ValueError("invalid pcap global header")

        magic = global_header[:4]
        if magic == b"\xd4\xc3\xb2\xa1":
            endian = "<"
        elif magic == b"\xa1\xb2\xc3\xd4":
            endian = ">"
        else:
            raise ValueError("unsupported pcap endianness")

        while True:
            record_header = handle.read(16)
            if not record_header:
                break
            if len(record_header) != 16:
                raise ValueError("truncated pcap record header")
            ts_sec, ts_usec, incl_len, _orig_len = struct.unpack(
                f"{endian}IIII", record_header
            )
            frame = handle.read(incl_len)
            if len(frame) != incl_len:
                raise ValueError("truncated pcap packet data")
            packets.append(parse_frame(frame, ts_sec + ts_usec / 1_000_000))
    return packets


def parse_frame(frame, timestamp):
    packet = {
        "timestamp": timestamp,
        "eth_src": None,
        "eth_dst": None,
        "protocol": None,
        "src_ip": None,
        "dst_ip": None,
        "src_port": None,
        "dst_port": None,
        "tcp_flags": 0,
    }

    if len(frame) < 14:
        return packet

    packet["eth_dst"] = format_mac(frame[0:6])
    packet["eth_src"] = format_mac(frame[6:12])
    ethertype = struct.unpack("!H", frame[12:14])[0]

    if ethertype == 0x0806 and len(frame) >= 42:
        packet["protocol"] = "ARP"
        packet["src_ip"] = format_ip(frame[28:32])
        packet["dst_ip"] = format_ip(frame[38:42])
        return packet

    if ethertype != 0x0800 or len(frame) < 34:
        return packet

    packet["protocol"] = "IP"
    ip_offset = 14
    ihl = (frame[ip_offset] & 0x0F) * 4
    if len(frame) < ip_offset + ihl:
        return packet

    proto = frame[ip_offset + 9]
    packet["src_ip"] = format_ip(frame[ip_offset + 12 : ip_offset + 16])
    packet["dst_ip"] = format_ip(frame[ip_offset + 16 : ip_offset + 20])
    payload_offset = ip_offset + ihl

    if proto == 6 and len(frame) >= payload_offset + 20:
        packet["protocol"] = "TCP"
        packet["src_port"], packet["dst_port"] = struct.unpack(
            "!HH", frame[payload_offset : payload_offset + 4]
        )
        packet["tcp_flags"] = frame[payload_offset + 13]
    elif proto == 17 and len(frame) >= payload_offset + 8:
        packet["protocol"] = "UDP"
        packet["src_port"], packet["dst_port"] = struct.unpack(
            "!HH", frame[payload_offset : payload_offset + 4]
        )

    return packet


def is_private_ip(ip):
    return ip is not None and ipaddress.ip_address(ip).is_private


def is_multicast_or_broadcast(ip):
    if ip is None:
        return False
    addr = ipaddress.ip_address(ip)
    return addr.is_multicast or ip == "255.255.255.255"


def is_broadcast_packet(packet):
    return packet["eth_dst"] == "ff:ff:ff:ff:ff:ff" or is_multicast_or_broadcast(
        packet["dst_ip"]
    )


def packets_per_minute(packets):
    if not packets:
        return 0.0, 0
    start = packets[0]["timestamp"]
    buckets = defaultdict(int)
    for packet in packets:
        bucket = int((packet["timestamp"] - start) / 60)
        buckets[bucket] += 1
    counts = list(buckets.values())
    return sum(counts) / len(counts), max(counts)


def build_summary(packets):
    avg_ppm, max_ppm = packets_per_minute(packets)
    ratio = (max_ppm / avg_ppm) if avg_ppm else 0.0
    return {
        "total_packets": len(packets),
        "ip_packets": sum(1 for packet in packets if packet["protocol"] in {"TCP", "UDP", "IP"}),
        "tcp_packets": sum(1 for packet in packets if packet["protocol"] == "TCP"),
        "udp_packets": sum(1 for packet in packets if packet["protocol"] == "UDP"),
        "arp_packets": sum(1 for packet in packets if packet["protocol"] == "ARP"),
        "broadcast_packets": sum(1 for packet in packets if is_broadcast_packet(packet)),
        "external_packets": sum(
            1
            for packet in packets
            if packet["protocol"] in {"TCP", "UDP"}
            and not is_multicast_or_broadcast(packet["dst_ip"])
            and (
                not is_private_ip(packet["src_ip"]) or not is_private_ip(packet["dst_ip"])
            )
        ),
        "packets_per_minute_avg": round4(avg_ppm),
        "packets_per_minute_max": max_ppm,
        "peak_to_avg_ratio": round4(ratio),
    }


def compute_broadcast_noise(packets, inventory_by_ip, total_broadcast_packets):
    per_src = Counter()
    channels = defaultdict(Counter)

    for packet in packets:
        if not is_broadcast_packet(packet):
            continue
        if packet["src_ip"] not in inventory_by_ip:
            continue
        per_src[packet["src_ip"]] += 1
        if packet["protocol"] == "ARP":
            channel = "arp"
        elif packet["protocol"] == "UDP" and packet["dst_ip"] == "224.0.0.251" and packet["dst_port"] == 5353:
            channel = "mdns"
        elif packet["protocol"] == "UDP" and packet["dst_ip"] == "239.255.255.250" and packet["dst_port"] == 1900:
            channel = "ssdp"
        elif packet["protocol"] == "UDP" and packet["dst_ip"] == "224.0.0.252" and packet["dst_port"] == 5355:
            channel = "llmnr"
        else:
            channel = "other"
        channels[packet["src_ip"]][channel] += 1

    if not per_src:
        return {
            "device_id": None,
            "ip": None,
            "mac": None,
            "broadcast_packets": 0,
            "broadcast_share": 0.0,
            "top_channels": [],
            "classification": "none",
        }

    winner_ip = sorted(per_src.items(), key=lambda item: (-item[1], item[0]))[0][0]
    winner = inventory_by_ip[winner_ip]
    top_channels = [
        name
        for name, count in sorted(
            channels[winner_ip].items(), key=lambda item: (-item[1], item[0])
        )
        if count > 0
    ][:3]

    share = (per_src[winner_ip] / total_broadcast_packets) if total_broadcast_packets else 0.0
    return {
        "device_id": winner["device_id"],
        "ip": winner["ip"],
        "mac": winner["mac"],
        "broadcast_packets": per_src[winner_ip],
        "broadcast_share": round4(share),
        "top_channels": top_channels,
        "classification": "broadcast-noise",
    }


def qualifying_bidirectional_flows(packets):
    flow_keys = set()
    for packet in packets:
        if packet["protocol"] not in {"TCP", "UDP"}:
            continue
        if not (is_private_ip(packet["src_ip"]) and is_private_ip(packet["dst_ip"])):
            continue
        if is_multicast_or_broadcast(packet["dst_ip"]):
            continue
        flow_keys.add(
            (
                packet["src_ip"],
                packet["dst_ip"],
                packet["src_port"],
                packet["dst_port"],
                packet["protocol"],
            )
        )

    return {
        key
        for key in flow_keys
        if (key[1], key[0], key[3], key[2], key[4]) in flow_keys
    }


def compute_service_diffusion(packets, inventory_by_ip):
    qualifying = qualifying_bidirectional_flows(packets)
    candidates = []

    for src_ip in inventory_by_ip:
        targets = set()
        dst_port_counter = Counter()
        for packet in packets:
            key = (
                packet["src_ip"],
                packet["dst_ip"],
                packet["src_port"],
                packet["dst_port"],
                packet["protocol"],
            )
            if packet["src_ip"] != src_ip or key not in qualifying:
                continue
            targets.add(packet["dst_ip"])
            dst_port_counter[packet["dst_port"]] += 1

        if not targets:
            continue

        candidates.append(
            (
                len(targets),
                len(dst_port_counter),
                shannon_entropy(dst_port_counter),
                src_ip,
            )
        )

    if not candidates:
        return {
            "device_id": None,
            "ip": None,
            "unique_internal_targets": 0,
            "unique_dst_ports": 0,
            "dst_port_entropy": 0.0,
            "classification": "none",
        }

    targets, ports, entropy, src_ip = sorted(
        candidates, key=lambda item: (-item[0], -item[1], item[3])
    )[0]
    winner = inventory_by_ip[src_ip]
    return {
        "device_id": winner["device_id"],
        "ip": winner["ip"],
        "unique_internal_targets": targets,
        "unique_dst_ports": ports,
        "dst_port_entropy": round4(entropy),
        "classification": "controller-fanout" if ports < 100 else "suspicious-fanout",
    }


def compute_beaconing(packets, inventory_by_ip):
    groups = defaultdict(list)

    for packet in packets:
        if packet["protocol"] not in {"TCP", "UDP"}:
            continue
        if packet["src_ip"] not in inventory_by_ip:
            continue
        if not packet["dst_ip"] or is_private_ip(packet["dst_ip"]) or is_multicast_or_broadcast(packet["dst_ip"]):
            continue
        key = (packet["src_ip"], packet["dst_ip"], packet["dst_port"], packet["protocol"])
        groups[key].append(packet["timestamp"])

    candidates = []
    for key, timestamps in groups.items():
        if len(timestamps) < 8:
            continue
        timestamps.sort()
        iats = [timestamps[idx + 1] - timestamps[idx] for idx in range(len(timestamps) - 1)]
        mean = sum(iats) / len(iats)
        variance = sum((value - mean) ** 2 for value in iats) / len(iats)
        cv = (math.sqrt(variance) / mean) if mean else 0.0
        candidates.append((cv, -len(timestamps), key, median(iats)))

    if not candidates:
        return {
            "device_id": None,
            "src_ip": None,
            "dst_ip": None,
            "dst_port": 0,
            "protocol": None,
            "flow_packets": 0,
            "median_interval_seconds": 0.0,
            "interval_cv": 0.0,
            "classification": "none",
        }

    cv, neg_flow_packets, key, med = sorted(
        candidates, key=lambda item: (item[0], item[1], item[2])
    )[0]
    src_ip, dst_ip, dst_port, protocol = key
    classification = "periodic-beacon" if cv < 0.15 and 20 <= med <= 90 else "not-beaconing"
    return {
        "device_id": inventory_by_ip[src_ip]["device_id"],
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "dst_port": dst_port,
        "protocol": protocol,
        "flow_packets": -neg_flow_packets,
        "median_interval_seconds": round4(med),
        "interval_cv": round4(cv),
        "classification": classification,
    }


def compute_scan(packets, inventory_by_ip):
    dst_port_counters = defaultdict(Counter)
    syn_only = Counter()
    totals = Counter()
    target_counters = defaultdict(Counter)

    for packet in packets:
        if packet["protocol"] != "TCP":
            continue
        if packet["src_ip"] not in inventory_by_ip:
            continue

        dst_port_counters[packet["src_ip"]][packet["dst_port"]] += 1
        totals[packet["src_ip"]] += 1
        target_counters[packet["src_ip"]][packet["dst_ip"]] += 1

        flags = packet["tcp_flags"]
        if (flags & 0x02) and not (flags & 0x10):
            syn_only[packet["src_ip"]] += 1

    candidates = []
    for src_ip, counter in dst_port_counters.items():
        total = totals[src_ip]
        if total < 50:
            continue
        unique_ports = len(counter)
        entropy = shannon_entropy(counter)
        syn_ratio = (syn_only[src_ip] / total) if total else 0.0
        if entropy > 6.0 and syn_ratio > 0.7 and unique_ports > 100:
            target_ip = sorted(
                target_counters[src_ip].items(), key=lambda item: (-item[1], item[0])
            )[0][0]
            candidates.append((unique_ports, entropy, src_ip, syn_ratio, target_ip))

    if not candidates:
        return {
            "device_id": None,
            "src_ip": None,
            "target_ip": None,
            "unique_dst_ports": 0,
            "dst_port_entropy": 0.0,
            "syn_only_ratio": 0.0,
            "classification": "none",
        }

    unique_ports, entropy, src_ip, syn_ratio, target_ip = sorted(
        candidates, key=lambda item: (-item[0], -item[1], item[2])
    )[0]
    winner = inventory_by_ip[src_ip]
    return {
        "device_id": winner["device_id"],
        "src_ip": src_ip,
        "target_ip": target_ip,
        "unique_dst_ports": unique_ports,
        "dst_port_entropy": round4(entropy),
        "syn_only_ratio": round4(syn_ratio),
        "classification": "scan",
    }


inventory_by_ip = load_inventory(INVENTORY_FILE)
packets = parse_pcap(INPUT_PCAP)
packets.sort(key=lambda packet: packet["timestamp"])

capture_summary = build_summary(packets)
broadcast_noise = compute_broadcast_noise(
    packets, inventory_by_ip, capture_summary["broadcast_packets"]
)
service_diffusion = compute_service_diffusion(packets, inventory_by_ip)
beaconing = compute_beaconing(packets, inventory_by_ip)
scan = compute_scan(packets, inventory_by_ip)

verdict = {
    "has_beaconing": beaconing["classification"] == "periodic-beacon",
    "has_scan": scan["classification"] == "scan",
    "has_flood_like": capture_summary["peak_to_avg_ratio"] > 20,
}
verdict["is_noise_only"] = not any(verdict.values())

result = {
    "capture_summary": capture_summary,
    "broadcast_noise": broadcast_noise,
    "service_diffusion": service_diffusion,
    "beaconing": beaconing,
    "scan": scan,
    "verdict": verdict,
}

OUTPUT_FILE.write_text(json.dumps(result, indent=2, sort_keys=True))
print(OUTPUT_FILE)
PY
