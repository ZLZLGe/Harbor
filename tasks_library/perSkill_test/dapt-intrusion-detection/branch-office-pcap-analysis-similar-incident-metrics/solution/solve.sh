#!/bin/bash

set -euo pipefail

python3 <<'PY'
import csv
import sys

sys.path.insert(0, "/root/skills/pcap-analysis")

from pcap_utils import (  # noqa: E402
    detect_beaconing,
    detect_dos_pattern,
    detect_port_scan,
    flow_metrics,
    graph_metrics,
    iat_stats,
    ip_counters,
    load_packets,
    packets_per_minute_stats,
    packet_timestamps,
    port_counters,
    producer_consumer_counts,
    shannon_entropy,
    split_by_protocol,
)

PCAP_FILE = "/root/branch_office_incident.pcap"
CSV_FILE = "/root/branch_incident_metrics.csv"

packets = load_packets(PCAP_FILE)
parts = split_by_protocol(packets)
timestamps = packet_timestamps(packets)

results = {}

results["protocol_tcp"] = len(parts["tcp"])
results["protocol_udp"] = len(parts["udp"])
results["protocol_icmp"] = len(parts["icmp"])
results["protocol_arp"] = len(parts["arp"])
results["protocol_ip_total"] = len(parts["ip"])

results["duration_seconds"] = round(timestamps[-1] - timestamps[0], 2) if len(timestamps) > 1 else 0
ppm = packets_per_minute_stats(timestamps)
if ppm:
    results.update(ppm)
else:
    results["packets_per_minute_avg"] = 0
    results["packets_per_minute_max"] = 0
    results["packets_per_minute_min"] = 0

packet_sizes = [len(pkt) for pkt in packets]
results["total_bytes"] = sum(packet_sizes)
results["avg_packet_size"] = round(results["total_bytes"] / len(packet_sizes), 2) if packet_sizes else 0
results["min_packet_size"] = min(packet_sizes) if packet_sizes else 0
results["max_packet_size"] = max(packet_sizes) if packet_sizes else 0

src_ports, dst_ports = port_counters(parts["tcp"], parts["udp"])
src_ips, dst_ips = ip_counters(parts["ip"])
results["src_ip_entropy"] = shannon_entropy(src_ips)
results["dst_ip_entropy"] = shannon_entropy(dst_ips)
results["src_port_entropy"] = shannon_entropy(src_ports)
results["dst_port_entropy"] = shannon_entropy(dst_ports)
results["unique_src_ports"] = len(src_ports)
results["unique_dst_ports"] = len(dst_ports)

graph = graph_metrics(parts["ip"])
results["num_nodes"] = graph["num_nodes"]
results["num_edges"] = graph["num_edges"]
results["network_density"] = graph["network_density"]
results["max_outdegree"] = graph["max_outdegree"]
results["max_indegree"] = graph["max_indegree"]
all_nodes = graph["_graph_state"][2]

iat = iat_stats(timestamps)
if iat:
    results.update(iat)
else:
    results["iat_mean"] = 0
    results["iat_variance"] = 0
    results["iat_cv"] = 0
results.update(producer_consumer_counts(parts["ip"], all_nodes))

results.update(flow_metrics(parts["tcp"], parts["udp"]))

has_port_scan = detect_port_scan(parts["tcp"])
has_dos = detect_dos_pattern(results["packets_per_minute_avg"], results["packets_per_minute_max"])
has_beaconing = detect_beaconing(results["iat_cv"])
results["has_port_scan"] = "true" if has_port_scan else "false"
results["has_dos_pattern"] = "true" if has_dos else "false"
results["has_beaconing"] = "true" if has_beaconing else "false"
results["is_traffic_benign"] = "true" if not (has_port_scan or has_dos or has_beaconing) else "false"

rows = []
with open(CSV_FILE, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

with open(CSV_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
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
