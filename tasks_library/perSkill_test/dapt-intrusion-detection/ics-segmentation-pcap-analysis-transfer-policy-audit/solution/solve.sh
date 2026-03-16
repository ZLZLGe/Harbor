#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import ipaddress
import json
import struct
from collections import Counter, defaultdict

PCAP_FILE = "/root/packets.pcap"
INVENTORY_FILE = "/root/asset_inventory.csv"
POLICY_FILE = "/root/zone_policy.json"
OUTPUT_FILE = "/root/ot_policy_audit.json"


def load_inventory(path):
    assets = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            assets[row["ip"]] = {
                "asset_name": row["asset_name"],
                "zone": row["zone"],
                "role": row["role"],
                "notes": row["notes"],
            }
    return assets


def load_policy(path):
    with open(path) as f:
        raw = json.load(f)
    return {
        (rule["src_zone"], rule["dst_zone"], rule["protocol"])
        for rule in raw["allowed_rules"]
    }


def iter_pcap_ipv4_packets(path):
    with open(path, "rb") as f:
        global_header = f.read(24)
        if len(global_header) != 24:
            raise ValueError("Invalid PCAP global header")
        magic = global_header[:4]
        if magic == b"\xd4\xc3\xb2\xa1":
            endian = "<"
        elif magic == b"\xa1\xb2\xc3\xd4":
            endian = ">"
        else:
            raise ValueError("Unsupported PCAP format")

        while True:
            packet_header = f.read(16)
            if not packet_header:
                break
            if len(packet_header) != 16:
                raise ValueError("Truncated PCAP packet header")
            _, _, incl_len, _ = struct.unpack(endian + "IIII", packet_header)
            data = f.read(incl_len)
            if len(data) != incl_len:
                raise ValueError("Truncated PCAP packet data")
            if len(data) < 34:
                continue
            ether_type = struct.unpack("!H", data[12:14])[0]
            if ether_type != 0x0800:
                continue
            ip_packet = data[14:]
            ihl = (ip_packet[0] & 0x0F) * 4
            if len(ip_packet) < ihl:
                continue
            src_ip = str(ipaddress.ip_address(ip_packet[12:16]))
            dst_ip = str(ipaddress.ip_address(ip_packet[16:20]))
            protocol_number = ip_packet[9]
            yield src_ip, dst_ip, protocol_number, ip_packet[ihl:]


def is_audited_unicast(ip_text):
    addr = ipaddress.ip_address(ip_text)
    return not (addr.is_multicast or ip_text in {"0.0.0.0", "255.255.255.255"})


def protocol_name(protocol_number):
    if protocol_number == 6:
        return "TCP"
    if protocol_number == 17:
        return "UDP"
    if protocol_number == 1:
        return "ICMP"
    return None


assets = load_inventory(INVENTORY_FILE)
allowed_rules = load_policy(POLICY_FILE)

edge_packets = Counter()
edge_ports = defaultdict(set)
active_assets = set()

for src_ip, dst_ip, proto_num, payload in iter_pcap_ipv4_packets(PCAP_FILE):
    proto = protocol_name(proto_num)
    if proto is None:
        continue
    if src_ip not in assets or dst_ip not in assets:
        continue
    if not (is_audited_unicast(src_ip) and is_audited_unicast(dst_ip)):
        continue

    edge = (src_ip, dst_ip, proto)
    edge_packets[edge] += 1
    active_assets.add(src_ip)
    active_assets.add(dst_ip)

    if proto in {"TCP", "UDP"} and len(payload) >= 4:
        dst_port = struct.unpack("!H", payload[2:4])[0]
        edge_ports[edge].add(dst_port)

communication_graph = []
violations = []
violating_direction_counts = Counter()
violating_direction_packet_counts = Counter()
allowed_edge_count = 0
allowed_packet_count = 0
cross_zone_edge_count = 0

for edge in sorted(edge_packets):
    src_ip, dst_ip, proto = edge
    src_asset = assets[src_ip]
    dst_asset = assets[dst_ip]
    direction = f"{src_asset['zone']}->{dst_asset['zone']}"
    cross_zone = src_asset["zone"] != dst_asset["zone"]
    allowed = (not cross_zone) or (
        src_asset["zone"], dst_asset["zone"], proto
    ) in allowed_rules
    record = {
        "src_ip": src_ip,
        "src_asset": src_asset["asset_name"],
        "src_zone": src_asset["zone"],
        "dst_ip": dst_ip,
        "dst_asset": dst_asset["asset_name"],
        "dst_zone": dst_asset["zone"],
        "protocol": proto,
        "packet_count": edge_packets[edge],
        "dst_ports": sorted(edge_ports.get(edge, set())),
        "cross_zone": cross_zone,
        "direction": direction,
        "status": "allowed" if allowed else "violation",
    }
    communication_graph.append(record)

    if cross_zone:
        cross_zone_edge_count += 1

    if allowed:
        allowed_edge_count += 1
        allowed_packet_count += edge_packets[edge]
    else:
        violating_direction_counts[direction] += 1
        violating_direction_packet_counts[direction] += edge_packets[edge]
        violations.append({**record, "reason": "no matching allow rule"})

result = {
    "summary": {
        "audited_asset_count": len(active_assets),
        "audited_packet_count": sum(edge_packets.values()),
        "directed_edge_count": len(communication_graph),
        "allowed_edge_count": allowed_edge_count,
        "allowed_packet_count": allowed_packet_count,
        "cross_zone_edge_count": cross_zone_edge_count,
        "violating_edge_count": len(violations),
        "violating_packet_count": sum(item["packet_count"] for item in violations),
        "violating_direction_counts": dict(sorted(violating_direction_counts.items())),
        "violating_direction_packet_counts": dict(
            sorted(violating_direction_packet_counts.items())
        ),
    },
    "communication_graph": communication_graph,
    "violations": violations,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(result, f, indent=2, sort_keys=False)
    f.write("\n")
PY
