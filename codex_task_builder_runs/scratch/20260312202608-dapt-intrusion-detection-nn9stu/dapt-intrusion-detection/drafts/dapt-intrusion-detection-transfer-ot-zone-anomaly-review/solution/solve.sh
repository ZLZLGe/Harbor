#!/bin/bash

set -euo pipefail

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INPUT_PCAP="${INPUT_PCAP:-/root/ot_zone_capture.pcap}"
INVENTORY_FILE="${INVENTORY_FILE:-/root/ot_asset_inventory.json}"
OUTPUT_FILE="${OUTPUT_FILE:-${PRIMARY_OUTPUT_FILE:-/root/ot_zone_risk_assessment.json}}"

if [ ! -f "$INPUT_PCAP" ]; then
  INPUT_PCAP="$TASK_ROOT/environment/ot_zone_capture.pcap"
fi

if [ ! -f "$INVENTORY_FILE" ]; then
  INVENTORY_FILE="$TASK_ROOT/environment/ot_asset_inventory.json"
fi

if [ ! -d "$(dirname "$OUTPUT_FILE")" ] || [ ! -w "$(dirname "$OUTPUT_FILE")" ]; then
  OUTPUT_FILE="$TASK_ROOT/.tmp_ot_zone_risk_assessment.json"
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


INPUT_PCAP = Path(os.environ["INPUT_PCAP"])
INVENTORY_FILE = Path(os.environ["INVENTORY_FILE"])
OUTPUT_FILE = Path(os.environ["OUTPUT_FILE"])


def round4(value):
    return round(float(value), 4)


def median(values):
    ordered = sorted(values)
    size = len(ordered)
    if size == 0:
        return 0.0
    middle = size // 2
    if size % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def shannon_entropy(counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        if count <= 0:
            continue
        probability = count / total
        entropy -= probability * math.log2(probability)
    return round4(entropy)


def interval_summary(timestamps):
    if len(timestamps) < 2:
        return 0.0, 0.0
    ordered = sorted(timestamps)
    iats = [ordered[index + 1] - ordered[index] for index in range(len(ordered) - 1)]
    mean_iat = sum(iats) / len(iats)
    variance = sum((value - mean_iat) ** 2 for value in iats) / len(iats)
    interval_cv = math.sqrt(variance) / mean_iat if mean_iat else 0.0
    return round4(median(iats)), round4(interval_cv)


def format_mac(raw):
    return ":".join(f"{byte:02x}" for byte in raw)


def format_ip(raw):
    return ".".join(str(byte) for byte in raw)


def load_inventory(path):
    items = json.loads(path.read_text())
    by_ip = {}
    by_asset_id = {}
    for item in items:
        by_ip[item["ip"]] = item
        by_asset_id[item["asset_id"]] = item
    return items, by_ip, by_asset_id


def parse_pcap(path):
    packets = []
    with path.open("rb") as handle:
        header = handle.read(24)
        if len(header) != 24:
            raise ValueError("invalid pcap global header")

        magic = header[:4]
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
    packets.sort(key=lambda item: item["timestamp"])
    return packets


def parse_frame(frame, timestamp):
    packet = {
        "timestamp": float(timestamp),
        "length": len(frame),
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

    ip_offset = 14
    ihl = (frame[ip_offset] & 0x0F) * 4
    if len(frame) < ip_offset + ihl:
        return packet

    protocol_number = frame[ip_offset + 9]
    packet["src_ip"] = format_ip(frame[ip_offset + 12 : ip_offset + 16])
    packet["dst_ip"] = format_ip(frame[ip_offset + 16 : ip_offset + 20])
    transport_offset = ip_offset + ihl

    if protocol_number == 6 and len(frame) >= transport_offset + 20:
        packet["protocol"] = "TCP"
        packet["src_port"], packet["dst_port"] = struct.unpack(
            "!HH", frame[transport_offset : transport_offset + 4]
        )
        packet["tcp_flags"] = frame[transport_offset + 13]
    elif protocol_number == 17 and len(frame) >= transport_offset + 8:
        packet["protocol"] = "UDP"
        packet["src_port"], packet["dst_port"] = struct.unpack(
            "!HH", frame[transport_offset : transport_offset + 4]
        )

    return packet


def pick_role_asset(items, role_name):
    matches = sorted(
        (item for item in items if item["role"] == role_name),
        key=lambda item: item["asset_id"],
    )
    return matches[0] if matches else None


def choose_group(groups, min_packets):
    candidates = []
    for key, timestamps in groups.items():
        if len(timestamps) < min_packets:
            continue
        median_interval, interval_cv = interval_summary(timestamps)
        candidates.append(
            {
                "key": key,
                "flow_packets": len(timestamps),
                "median_interval_seconds": median_interval,
                "interval_cv": interval_cv,
            }
        )
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            item["interval_cv"],
            -item["flow_packets"],
            item["key"],
        )
    )
    return candidates[0]


inventory_items, inventory_by_ip, inventory_by_asset_id = load_inventory(INVENTORY_FILE)
packets = parse_pcap(INPUT_PCAP)

if not packets:
    raise ValueError("empty capture")

tcp_packets = [packet for packet in packets if packet["protocol"] == "TCP"]
udp_packets = [packet for packet in packets if packet["protocol"] == "UDP"]
arp_packets = [packet for packet in packets if packet["protocol"] == "ARP"]
ip_packets = tcp_packets + udp_packets

internal_ip_packets = [
    packet
    for packet in ip_packets
    if packet["src_ip"] in inventory_by_ip and packet["dst_ip"] in inventory_by_ip
]
external_ip_packets = [
    packet
    for packet in ip_packets
    if packet["src_ip"] not in inventory_by_ip or packet["dst_ip"] not in inventory_by_ip
]

start_time = packets[0]["timestamp"]
end_time = packets[-1]["timestamp"]
minute_buckets = defaultdict(int)
for packet in packets:
    minute_buckets[int((packet["timestamp"] - start_time) / 60)] += 1

controllers = sorted(
    item["asset_id"] for item in inventory_items if item["role"] == "controller"
)
hmi_asset = pick_role_asset(inventory_items, "hmi")
engineering_asset = pick_role_asset(inventory_items, "engineering-station")

internal_flows = set()
for packet in internal_ip_packets:
    internal_flows.add(
        (
            packet["src_ip"],
            packet["dst_ip"],
            packet["src_port"],
            packet["dst_port"],
            packet["protocol"],
        )
    )

bidirectional_pairs = set()
controller_hmi_pairs = set()
engineering_controller_pairs = set()
controller_service_ports = set()

for flow in internal_flows:
    reverse = (flow[1], flow[0], flow[3], flow[2], flow[4])
    if reverse not in internal_flows:
        continue
    pair = tuple(sorted((flow, reverse)))
    if pair in bidirectional_pairs:
        continue
    bidirectional_pairs.add(pair)

    endpoint_roles = {inventory_by_ip[flow[0]]["role"], inventory_by_ip[flow[1]]["role"]}
    endpoint_assets = tuple(
        sorted(
            (
                inventory_by_ip[flow[0]]["asset_id"],
                inventory_by_ip[flow[1]]["asset_id"],
            )
        )
    )

    if endpoint_roles == {"controller", "hmi"}:
        controller_hmi_pairs.add(endpoint_assets)
    if endpoint_roles == {"controller", "engineering-station"}:
        engineering_controller_pairs.add(endpoint_assets)

    for directional_flow in pair:
        src_item = inventory_by_ip[directional_flow[0]]
        dst_item = inventory_by_ip[directional_flow[1]]
        if (
            directional_flow[4] == "TCP"
            and src_item["role"] in {"hmi", "engineering-station"}
            and dst_item["role"] == "controller"
        ):
            controller_service_ports.add(directional_flow[3])

control_groups = defaultdict(list)
maintenance_groups = defaultdict(list)
external_groups = defaultdict(list)

for packet in tcp_packets:
    src_item = inventory_by_ip.get(packet["src_ip"])
    dst_item = inventory_by_ip.get(packet["dst_ip"])
    if (
        src_item
        and dst_item
        and src_item["role"] == "hmi"
        and dst_item["role"] == "controller"
        and packet["dst_port"] in controller_service_ports
    ):
        key = (
            src_item["asset_id"],
            dst_item["asset_id"],
            packet["dst_port"],
            "TCP",
        )
        control_groups[key].append(packet["timestamp"])
    if (
        src_item
        and dst_item
        and src_item["role"] == "engineering-station"
        and dst_item["role"] == "controller"
        and packet["dst_port"] in controller_service_ports
    ):
        key = (
            src_item["asset_id"],
            dst_item["asset_id"],
            packet["dst_port"],
            "TCP",
        )
        maintenance_groups[key].append(packet["timestamp"])

for packet in ip_packets:
    src_item = inventory_by_ip.get(packet["src_ip"])
    if (
        src_item
        and src_item["role"] == "engineering-station"
        and packet["dst_ip"] not in inventory_by_ip
    ):
        key = (
            src_item["asset_id"],
            packet["dst_ip"],
            packet["dst_port"],
            packet["protocol"],
        )
        external_groups[key].append(packet["timestamp"])

control_choice = choose_group(control_groups, 8)
maintenance_choice = choose_group(maintenance_groups, 4)
external_choice = choose_group(external_groups, 8)

src_ip_counter = Counter(packet["src_ip"] for packet in ip_packets)
dst_ip_counter = Counter(packet["dst_ip"] for packet in ip_packets)
dst_port_counter = Counter(packet["dst_port"] for packet in ip_packets)

eng_ip = engineering_asset["ip"] if engineering_asset else None
eng_target_counter = Counter(
    packet["dst_ip"] for packet in ip_packets if packet["src_ip"] == eng_ip
)
eng_dst_port_counter = Counter(
    packet["dst_port"] for packet in ip_packets if packet["src_ip"] == eng_ip
)

scan_port_counts = defaultdict(Counter)
scan_syn_only_counts = defaultdict(int)
scan_tcp_totals = defaultdict(int)
scan_target_counts = defaultdict(Counter)

for packet in tcp_packets:
    if packet["src_ip"] not in inventory_by_ip or packet["dst_ip"] not in inventory_by_ip:
        continue
    source_ip = packet["src_ip"]
    scan_port_counts[source_ip][packet["dst_port"]] += 1
    scan_tcp_totals[source_ip] += 1
    scan_target_counts[source_ip][packet["dst_ip"]] += 1
    if packet["tcp_flags"] & 0x02 and not (packet["tcp_flags"] & 0x10):
        scan_syn_only_counts[source_ip] += 1

scan_candidate = None
for source_ip, port_counter in scan_port_counts.items():
    total_tcp = scan_tcp_totals[source_ip]
    if total_tcp < 50:
        continue
    port_entropy = shannon_entropy(port_counter)
    syn_ratio = round4(scan_syn_only_counts[source_ip] / total_tcp) if total_tcp else 0.0
    unique_ports = len(port_counter)
    if port_entropy > 6.0 and syn_ratio > 0.7 and unique_ports > 100:
        target_ip = sorted(
            scan_target_counts[source_ip].items(),
            key=lambda item: (-item[1], inventory_by_ip[item[0]]["asset_id"]),
        )[0][0]
        candidate = {
            "source_ip": source_ip,
            "source_asset_id": inventory_by_ip[source_ip]["asset_id"],
            "target_ip": target_ip,
            "target_asset_id": inventory_by_ip[target_ip]["asset_id"],
            "unique_dst_ports": unique_ports,
            "dst_port_entropy": port_entropy,
            "syn_only_ratio": syn_ratio,
        }
        if scan_candidate is None or (
            candidate["unique_dst_ports"],
            candidate["dst_port_entropy"],
            -1,
        ) > (
            scan_candidate["unique_dst_ports"],
            scan_candidate["dst_port_entropy"],
            -1,
        ):
            scan_candidate = candidate
        elif (
            candidate["unique_dst_ports"] == scan_candidate["unique_dst_ports"]
            and candidate["dst_port_entropy"] == scan_candidate["dst_port_entropy"]
            and candidate["source_ip"] < scan_candidate["source_ip"]
        ):
            scan_candidate = candidate

if scan_candidate is not None:
    unanswered_scan_flows = 0
    for flow in internal_flows:
        if flow[0] != scan_candidate["source_ip"] or flow[4] != "TCP":
            continue
        reverse = (flow[1], flow[0], flow[3], flow[2], flow[4])
        if reverse not in internal_flows:
            unanswered_scan_flows += 1
else:
    unanswered_scan_flows = 0

burst_candidate = None
for item in inventory_items:
    source_packets = [
        packet
        for packet in ip_packets
        if packet["src_ip"] == item["ip"] and packet["protocol"] in {"TCP", "UDP"}
    ]
    if not source_packets:
        continue
    source_buckets = defaultdict(int)
    for packet in source_packets:
        source_buckets[int((packet["timestamp"] - start_time) / 60)] += 1
    counts = list(source_buckets.values())
    average_non_empty = sum(counts) / len(counts)
    max_bucket = max(counts)
    max_index = min(index for index, count in source_buckets.items() if count == max_bucket)
    candidate = {
        "asset_id": item["asset_id"],
        "minute_index": max_index,
        "burst_packets": max_bucket,
        "burst_ratio": round4(max_bucket / average_non_empty) if average_non_empty else 0.0,
    }
    if burst_candidate is None or (
        candidate["burst_ratio"],
        candidate["burst_packets"],
        tuple([-ord(char) for char in candidate["asset_id"]]),
    ) > (
        burst_candidate["burst_ratio"],
        burst_candidate["burst_packets"],
        tuple([-ord(char) for char in burst_candidate["asset_id"]]),
    ):
        burst_candidate = candidate
    elif (
        candidate["burst_ratio"] == burst_candidate["burst_ratio"]
        and candidate["burst_packets"] == burst_candidate["burst_packets"]
        and candidate["asset_id"] < burst_candidate["asset_id"]
    ):
        burst_candidate = candidate

has_scan = scan_candidate is not None
has_flood_like = (
    burst_candidate is not None
    and burst_candidate["burst_ratio"] > 20
    and burst_candidate["burst_packets"] >= 100
)
has_beaconing = (
    external_choice is not None
    and 20 <= external_choice["median_interval_seconds"] <= 90
    and external_choice["interval_cv"] < 0.15
)

control_loop = {
    "src_asset_id": "none",
    "dst_asset_id": "none",
    "dst_port": 0,
    "protocol": "none",
    "flow_packets": 0,
    "median_interval_seconds": 0,
    "interval_cv": 0,
}
if control_choice is not None:
    control_loop = {
        "src_asset_id": control_choice["key"][0],
        "dst_asset_id": control_choice["key"][1],
        "dst_port": control_choice["key"][2],
        "protocol": control_choice["key"][3],
        "flow_packets": control_choice["flow_packets"],
        "median_interval_seconds": control_choice["median_interval_seconds"],
        "interval_cv": control_choice["interval_cv"],
    }

maintenance_loop = {
    "src_asset_id": "none",
    "dst_asset_id": "none",
    "dst_port": 0,
    "protocol": "none",
    "flow_packets": 0,
    "median_interval_seconds": 0,
    "interval_cv": 0,
}
if maintenance_choice is not None:
    maintenance_loop = {
        "src_asset_id": maintenance_choice["key"][0],
        "dst_asset_id": maintenance_choice["key"][1],
        "dst_port": maintenance_choice["key"][2],
        "protocol": maintenance_choice["key"][3],
        "flow_packets": maintenance_choice["flow_packets"],
        "median_interval_seconds": maintenance_choice["median_interval_seconds"],
        "interval_cv": maintenance_choice["interval_cv"],
    }

external_candidate = {
    "src_asset_id": "none",
    "dst_ip": "none",
    "dst_port": 0,
    "protocol": "none",
    "flow_packets": 0,
    "median_interval_seconds": 0,
    "interval_cv": 0,
}
if external_choice is not None:
    external_candidate = {
        "src_asset_id": external_choice["key"][0],
        "dst_ip": external_choice["key"][1],
        "dst_port": external_choice["key"][2],
        "protocol": external_choice["key"][3],
        "flow_packets": external_choice["flow_packets"],
        "median_interval_seconds": external_choice["median_interval_seconds"],
        "interval_cv": external_choice["interval_cv"],
    }

result = {
    "capture_summary": {
        "total_packets": len(packets),
        "ip_packets": len(ip_packets),
        "tcp_packets": len(tcp_packets),
        "udp_packets": len(udp_packets),
        "arp_packets": len(arp_packets),
        "internal_ip_packets": len(internal_ip_packets),
        "external_ip_packets": len(external_ip_packets),
        "duration_seconds": round4(end_time - start_time),
        "active_minutes": len(minute_buckets),
    },
    "baseline": {
        "controller_assets": controllers,
        "hmi_asset_id": hmi_asset["asset_id"] if hmi_asset else "none",
        "engineering_asset_id": engineering_asset["asset_id"] if engineering_asset else "none",
        "controller_service_ports": sorted(controller_service_ports),
        "hmi_controller_pairs": len(controller_hmi_pairs),
        "engineering_controller_pairs": len(engineering_controller_pairs),
        "hmi_poll_median_interval_seconds": control_loop["median_interval_seconds"],
        "engineering_maintenance_median_interval_seconds": maintenance_loop["median_interval_seconds"],
    },
    "entropy_profile": {
        "src_ip_entropy": shannon_entropy(src_ip_counter),
        "dst_ip_entropy": shannon_entropy(dst_ip_counter),
        "dst_port_entropy": shannon_entropy(dst_port_counter),
        "eng_station_target_entropy": shannon_entropy(eng_target_counter),
        "eng_station_dst_port_entropy": shannon_entropy(eng_dst_port_counter),
    },
    "cadence_profile": {
        "control_loop": control_loop,
        "maintenance_loop": maintenance_loop,
        "external_candidate": external_candidate,
    },
    "bidirectional_relationships": {
        "unique_internal_flows": len(internal_flows),
        "bidirectional_internal_flow_pairs": len(bidirectional_pairs),
        "controller_hmi_bidirectional_pairs": len(controller_hmi_pairs),
        "engineering_controller_bidirectional_pairs": len(engineering_controller_pairs),
        "unanswered_scan_flows": unanswered_scan_flows,
    },
    "risk_assessment": {
        "scan_source_asset_id": scan_candidate["source_asset_id"] if scan_candidate else "none",
        "scan_target_asset_id": scan_candidate["target_asset_id"] if scan_candidate else "none",
        "scan_unique_dst_ports": scan_candidate["unique_dst_ports"] if scan_candidate else 0,
        "scan_dst_port_entropy": scan_candidate["dst_port_entropy"] if scan_candidate else 0,
        "scan_syn_only_ratio": scan_candidate["syn_only_ratio"] if scan_candidate else 0,
        "burst_source_asset_id": burst_candidate["asset_id"] if burst_candidate else "none",
        "burst_minute_index": burst_candidate["minute_index"] if burst_candidate else 0,
        "burst_packets": burst_candidate["burst_packets"] if burst_candidate else 0,
        "burst_ratio": burst_candidate["burst_ratio"] if burst_candidate else 0,
        "beacon_asset_id": external_candidate["src_asset_id"] if external_choice else "none",
        "beacon_dst_ip": external_candidate["dst_ip"] if external_choice else "none",
        "beacon_dst_port": external_candidate["dst_port"] if external_choice else 0,
        "beacon_protocol": external_candidate["protocol"] if external_choice else "none",
        "beacon_flow_packets": external_candidate["flow_packets"] if external_choice else 0,
        "beacon_median_interval_seconds": external_candidate["median_interval_seconds"] if external_choice else 0,
        "beacon_interval_cv": external_candidate["interval_cv"] if external_choice else 0,
        "has_scan": has_scan,
        "has_flood_like": has_flood_like,
        "has_beaconing": has_beaconing,
        "is_ot_zone_stable": not (has_scan or has_flood_like or has_beaconing),
    },
}

OUTPUT_FILE.write_text(json.dumps(result, indent=2, sort_keys=False))
PY
