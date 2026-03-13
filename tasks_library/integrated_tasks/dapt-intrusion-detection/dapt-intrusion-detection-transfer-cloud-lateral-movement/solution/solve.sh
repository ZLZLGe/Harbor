#!/bin/bash

set -euo pipefail

python3 <<'PY'
import csv
import math
import sys
from collections import defaultdict
from ipaddress import ip_address

sys.path.insert(0, "/root/skills/pcap-analysis")

from pcap_utils import (
    packet_timestamps,
    packets_per_minute_stats,
    port_scan_signals,
    shannon_entropy,
    split_by_protocol,
    load_packets,
)
from scapy.all import IP, TCP, UDP

PCAP_FILE = "/root/cloud_vpc_east_west.pcap"
CSV_FILE = "/root/cloud_lateral_report.csv"


def is_private_ipv4(value):
    try:
        return ip_address(value).is_private
    except ValueError:
        return False


def subnet_of(ip_text):
    parts = ip_text.split(".")
    return ".".join(parts[:3]) + ".0/24"


def median(values):
    ordered = sorted(values)
    size = len(ordered)
    if size == 0:
        return 0.0
    mid = size // 2
    if size % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


packets = load_packets(PCAP_FILE)
parts = split_by_protocol(packets)
ip_packets = [pkt for pkt in parts["ip"] if IP in pkt]
internal_ip_packets = [
    pkt
    for pkt in ip_packets
    if is_private_ipv4(pkt[IP].src) and is_private_ipv4(pkt[IP].dst)
]
internal_tcp_packets = [pkt for pkt in parts["tcp"] if IP in pkt and is_private_ipv4(pkt[IP].src) and is_private_ipv4(pkt[IP].dst)]
internal_udp_packets = [pkt for pkt in parts["udp"] if IP in pkt and is_private_ipv4(pkt[IP].src) and is_private_ipv4(pkt[IP].dst)]

results = {}

results["total_packets"] = len(packets)
results["total_bytes"] = sum(len(pkt) for pkt in packets)
results["protocol_tcp"] = len(parts["tcp"])
results["protocol_udp"] = len(parts["udp"])
results["protocol_ip_total"] = len(ip_packets)
results["dominant_protocol"] = "tcp" if results["protocol_tcp"] >= results["protocol_udp"] else "udp"

timestamps = packet_timestamps(packets)
results["duration_seconds"] = round(timestamps[-1] - timestamps[0], 2)
ppm = packets_per_minute_stats(timestamps)
results.update(ppm)

minute_buckets = defaultdict(int)
for ts in timestamps:
    minute_buckets[int((ts - timestamps[0]) / 60)] += 1
results["burst_minute_index"] = min(
    index for index, count in minute_buckets.items() if count == results["packets_per_minute_max"]
)
results["burst_ratio"] = round(
    results["packets_per_minute_max"] / results["packets_per_minute_avg"], 4
) if results["packets_per_minute_avg"] else 0

subnets = {
    subnet_of(pkt[IP].src) for pkt in internal_ip_packets
} | {subnet_of(pkt[IP].dst) for pkt in internal_ip_packets}
subnet_edges = {
    (subnet_of(pkt[IP].src), subnet_of(pkt[IP].dst))
    for pkt in internal_ip_packets
    if subnet_of(pkt[IP].src) != subnet_of(pkt[IP].dst)
}
results["num_subnets"] = len(subnets)
results["subnet_edges"] = len(subnet_edges)
if results["num_subnets"] < 2:
    results["subnet_graph_density"] = 0
else:
    results["subnet_graph_density"] = round(
        results["subnet_edges"] / (results["num_subnets"] * (results["num_subnets"] - 1)),
        6,
    )

fanout = defaultdict(set)
for pkt in internal_ip_packets:
    fanout[pkt[IP].src].add(pkt[IP].dst)
results["max_host_fanout"] = max((len(targets) for targets in fanout.values()), default=0)
fanout_candidates = [
    src_ip for src_ip, targets in fanout.items() if len(targets) == results["max_host_fanout"]
]
results["max_host_fanout_ip"] = min(fanout_candidates) if fanout_candidates else "none"

flows = set()
for pkt in internal_tcp_packets:
    flows.add((pkt[IP].src, pkt[IP].dst, pkt[TCP].sport, pkt[TCP].dport, "TCP"))
for pkt in internal_udp_packets:
    flows.add((pkt[IP].src, pkt[IP].dst, pkt[UDP].sport, pkt[UDP].dport, "UDP"))

results["unique_flows"] = len(flows)
results["tcp_flows"] = len([flow for flow in flows if flow[4] == "TCP"])
results["udp_flows"] = len([flow for flow in flows if flow[4] == "UDP"])
bidirectional = 0
for flow in flows:
    reverse = (flow[1], flow[0], flow[3], flow[2], flow[4])
    if reverse in flows:
        bidirectional += 1
results["bidirectional_flows"] = bidirectional // 2
results["flow_diversity_ratio"] = round(
    results["unique_flows"] / results["protocol_ip_total"], 4
) if results["protocol_ip_total"] else 0

src_port_counts, src_syn_only, src_total_tcp = port_scan_signals(internal_tcp_packets)
scan_candidates = []
for src_ip, port_counter in src_port_counts.items():
    total_tcp = src_total_tcp[src_ip]
    if total_tcp < 50:
        continue
    port_entropy = shannon_entropy(port_counter)
    syn_ratio = src_syn_only[src_ip] / total_tcp if total_tcp else 0
    unique_ports = len(port_counter)
    if port_entropy > 6.0 and syn_ratio > 0.7 and unique_ports > 100:
        scan_candidates.append(
            {
                "src_ip": src_ip,
                "unique_ports": unique_ports,
                "syn_ratio": round(syn_ratio, 4),
                "port_entropy": port_entropy,
            }
        )

if scan_candidates:
    scan_candidates.sort(
        key=lambda item: (-item["unique_ports"], -item["port_entropy"], item["src_ip"])
    )
    chosen_scan = scan_candidates[0]
    results["scan_source_ip"] = chosen_scan["src_ip"]
    results["scan_unique_dst_ports"] = chosen_scan["unique_ports"]
    results["scan_syn_ratio"] = chosen_scan["syn_ratio"]
    results["scan_dst_port_entropy"] = chosen_scan["port_entropy"]
else:
    results["scan_source_ip"] = "none"
    results["scan_unique_dst_ports"] = 0
    results["scan_syn_ratio"] = 0
    results["scan_dst_port_entropy"] = 0

c2_groups = defaultdict(list)
for pkt in internal_tcp_packets:
    c2_groups[(pkt[IP].src, pkt[IP].dst, pkt[TCP].dport, "TCP")].append(float(pkt.time))
for pkt in internal_udp_packets:
    c2_groups[(pkt[IP].src, pkt[IP].dst, pkt[UDP].dport, "UDP")].append(float(pkt.time))

c2_candidates = []
for key, group_timestamps in c2_groups.items():
    if len(group_timestamps) < 8:
        continue
    ordered = sorted(group_timestamps)
    iats = [ordered[index + 1] - ordered[index] for index in range(len(ordered) - 1)]
    if not iats:
        continue
    mean_iat = sum(iats) / len(iats)
    variance = sum((value - mean_iat) ** 2 for value in iats) / len(iats)
    median_iat = median(iats)
    if not (20 <= median_iat <= 90):
        continue
    interval_cv = round(math.sqrt(variance) / mean_iat, 4) if mean_iat else 0
    c2_candidates.append(
        {
            "key": key,
            "flow_packets": len(group_timestamps),
            "median_interval_seconds": round(median_iat, 4),
            "interval_cv": interval_cv,
        }
    )

if c2_candidates:
    c2_candidates.sort(
        key=lambda item: (
            item["interval_cv"],
            -item["flow_packets"],
            item["key"],
        )
    )
    chosen_c2 = c2_candidates[0]
    src_ip, dst_ip, dst_port, proto = chosen_c2["key"]
    results["c2_src_ip"] = src_ip
    results["c2_dst_ip"] = dst_ip
    results["c2_dst_port"] = dst_port
    results["c2_protocol"] = proto
    results["c2_flow_packets"] = chosen_c2["flow_packets"]
    results["c2_median_interval_seconds"] = chosen_c2["median_interval_seconds"]
    results["c2_interval_cv"] = chosen_c2["interval_cv"]
else:
    results["c2_src_ip"] = "none"
    results["c2_dst_ip"] = "none"
    results["c2_dst_port"] = 0
    results["c2_protocol"] = "none"
    results["c2_flow_packets"] = 0
    results["c2_median_interval_seconds"] = 0
    results["c2_interval_cv"] = 0

results["has_lateral_scan"] = "true" if scan_candidates else "false"
results["has_dos_burst"] = "true" if results["burst_ratio"] > 20 else "false"
results["has_periodic_c2"] = (
    "true"
    if results["c2_flow_packets"] >= 8
    and 20 <= results["c2_median_interval_seconds"] <= 90
    and results["c2_interval_cv"] < 0.15
    else "false"
)
results["is_east_west_benign"] = (
    "true"
    if not (
        results["has_lateral_scan"] == "true"
        or results["has_dos_burst"] == "true"
        or results["has_periodic_c2"] == "true"
    )
    else "false"
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
