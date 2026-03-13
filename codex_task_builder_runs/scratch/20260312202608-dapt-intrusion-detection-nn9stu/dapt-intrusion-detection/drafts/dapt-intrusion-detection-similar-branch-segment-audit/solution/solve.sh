#!/bin/bash

set -euo pipefail

python3 <<'PY'
import csv
import sys
from collections import defaultdict

sys.path.insert(0, "/root/skills/pcap-analysis")

from pcap_utils import (
    detect_beaconing,
    detect_dos_pattern,
    flow_metrics,
    graph_metrics,
    iat_stats,
    ip_counters,
    load_packets,
    packet_timestamps,
    packets_per_minute_stats,
    port_counters,
    port_scan_signals,
    shannon_entropy,
    split_by_protocol,
)

PCAP_FILE = "/root/branch_segment.pcap"
CSV_FILE = "/root/branch_segment_audit.csv"

packets = load_packets(PCAP_FILE)
parts = split_by_protocol(packets)
timestamps = packet_timestamps(packets)

results = {}

results["total_packets"] = len(packets)
results["protocol_tcp"] = len(parts["tcp"])
results["protocol_udp"] = len(parts["udp"])
results["protocol_icmp"] = len(parts["icmp"])
results["protocol_arp"] = len(parts["arp"])
results["protocol_ip_total"] = len(parts["ip"])

protocol_counts = {
    "tcp": results["protocol_tcp"],
    "udp": results["protocol_udp"],
    "icmp": results["protocol_icmp"],
    "arp": results["protocol_arp"],
}
results["dominant_protocol"] = max(protocol_counts, key=protocol_counts.get)

packet_sizes = [len(pkt) for pkt in packets]
results["total_bytes"] = sum(packet_sizes)
results["avg_packet_size"] = round(results["total_bytes"] / len(packet_sizes), 2)
results["min_packet_size"] = min(packet_sizes)
results["max_packet_size"] = max(packet_sizes)

results["duration_seconds"] = round(timestamps[-1] - timestamps[0], 2)
ppm_stats = packets_per_minute_stats(timestamps)
results.update(ppm_stats)

src_ports, dst_ports = port_counters(parts["tcp"], parts["udp"])
src_ips, dst_ips = ip_counters(parts["ip"])
results["src_ip_entropy"] = shannon_entropy(src_ips)
results["dst_ip_entropy"] = shannon_entropy(dst_ips)
results["src_port_entropy"] = shannon_entropy(src_ports)
results["dst_port_entropy"] = shannon_entropy(dst_ports)
results["unique_src_ports"] = len(src_ports)
results["unique_dst_ports"] = len(dst_ports)

graph = graph_metrics(parts["ip"])
for key in ("num_nodes", "num_edges", "network_density", "max_indegree", "max_outdegree"):
    results[key] = graph[key]

iat = iat_stats(timestamps)
results.update(iat)

flows = flow_metrics(parts["tcp"], parts["udp"])
results.update(flows)

src_port_counts, src_syn_only, src_total_tcp = port_scan_signals(parts["tcp"])
scanner_candidates = []
for src, port_counter in src_port_counts.items():
    total_tcp = src_total_tcp[src]
    if total_tcp < 50:
        continue
    port_entropy = shannon_entropy(port_counter)
    syn_ratio = src_syn_only[src] / total_tcp if total_tcp else 0.0
    unique_ports = len(port_counter)
    if port_entropy > 6.0 and syn_ratio > 0.7 and unique_ports > 100:
        scanner_candidates.append(
            {
                "ip": src,
                "unique_ports": unique_ports,
                "syn_ratio": syn_ratio,
                "port_entropy": port_entropy,
            }
        )

if scanner_candidates:
    scanner_candidates.sort(
        key=lambda item: (-item["unique_ports"], -item["port_entropy"], item["ip"])
    )
    suspect = scanner_candidates[0]
    results["suspected_scanner_ip"] = suspect["ip"]
    results["suspected_scanner_unique_dst_ports"] = suspect["unique_ports"]
    results["suspected_scanner_syn_ratio"] = round(suspect["syn_ratio"], 4)
    results["suspected_scanner_dst_port_entropy"] = suspect["port_entropy"]
else:
    results["suspected_scanner_ip"] = "none"
    results["suspected_scanner_unique_dst_ports"] = 0
    results["suspected_scanner_syn_ratio"] = 0
    results["suspected_scanner_dst_port_entropy"] = 0

has_port_scan = bool(scanner_candidates)
has_dos_pattern = detect_dos_pattern(
    results["packets_per_minute_avg"], results["packets_per_minute_max"]
)
has_beaconing = detect_beaconing(results["iat_cv"])

results["has_port_scan"] = "true" if has_port_scan else "false"
results["has_dos_pattern"] = "true" if has_dos_pattern else "false"
results["has_beaconing"] = "true" if has_beaconing else "false"
results["is_traffic_benign"] = (
    "true" if not (has_port_scan or has_dos_pattern or has_beaconing) else "false"
)

rows = []
with open(CSV_FILE, newline="") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        rows.append(row)

with open(CSV_FILE, "w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
    writer.writeheader()
    for row in rows:
        metric = (row.get("metric") or "").strip()
        if metric.startswith("#"):
            writer.writerow(row)
        elif metric in results:
            writer.writerow({"metric": metric, "value": results[metric]})
        else:
            writer.writerow(row)
PY
