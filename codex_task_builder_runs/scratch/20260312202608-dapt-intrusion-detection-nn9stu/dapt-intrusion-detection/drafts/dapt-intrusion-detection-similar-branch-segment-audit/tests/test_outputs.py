import csv
from pathlib import Path

import pytest

RESULTS_FILE = Path("/root/branch_segment_audit.csv")

FLOAT_TOLERANCE = 0.5
LARGE_INT_PERCENT_TOLERANCE = 0.01
ENTROPY_TOLERANCE = 0.05

EXPECTED_VALUES = {
    "total_packets": 114227,
    "dominant_protocol": "arp",
    "protocol_tcp": 32748,
    "protocol_udp": 25846,
    "protocol_icmp": 8,
    "protocol_arp": 54938,
    "protocol_ip_total": 58602,
    "duration_seconds": 26289.33,
    "packets_per_minute_avg": 260.20,
    "packets_per_minute_max": 2372,
    "packets_per_minute_min": 5,
    "total_bytes": 30896382,
    "avg_packet_size": 270.48,
    "min_packet_size": 42,
    "max_packet_size": 56538,
    "src_ip_entropy": 2.5004,
    "dst_ip_entropy": 2.4641,
    "src_port_entropy": 4.3526,
    "dst_port_entropy": 4.3072,
    "unique_src_ports": 1714,
    "unique_dst_ports": 1760,
    "num_nodes": 39,
    "num_edges": 59,
    "network_density": 0.039811,
    "max_indegree": 23,
    "max_outdegree": 27,
    "iat_mean": 0.230152,
    "iat_variance": 0.066897,
    "iat_cv": 1.1238,
    "unique_flows": 3695,
    "bidirectional_flows": 1758,
    "tcp_flows": 3481,
    "udp_flows": 214,
    "suspected_scanner_ip": "192.168.3.250",
    "suspected_scanner_unique_dst_ports": 128,
    "suspected_scanner_syn_ratio": 1.0,
    "suspected_scanner_dst_port_entropy": 7.0,
    "has_port_scan": "true",
    "has_dos_pattern": "false",
    "has_beaconing": "false",
    "is_traffic_benign": "false",
}

EXACT_INT_METRICS = {
    "total_packets",
    "protocol_tcp",
    "protocol_udp",
    "protocol_icmp",
    "protocol_arp",
    "protocol_ip_total",
    "packets_per_minute_max",
    "packets_per_minute_min",
    "total_bytes",
    "min_packet_size",
    "max_packet_size",
    "unique_src_ports",
    "unique_dst_ports",
    "num_nodes",
    "num_edges",
    "max_indegree",
    "max_outdegree",
    "unique_flows",
    "bidirectional_flows",
    "tcp_flows",
    "udp_flows",
    "suspected_scanner_unique_dst_ports",
}

ENTROPY_METRICS = {
    "src_ip_entropy",
    "dst_ip_entropy",
    "src_port_entropy",
    "dst_port_entropy",
    "suspected_scanner_dst_port_entropy",
}

STRING_METRICS = {
    "dominant_protocol",
    "suspected_scanner_ip",
    "has_port_scan",
    "has_dos_pattern",
    "has_beaconing",
    "is_traffic_benign",
}

_results_cache = None


def load_results():
    global _results_cache
    if _results_cache is not None:
        return _results_cache

    if not RESULTS_FILE.exists():
        return None

    parsed = {}
    with RESULTS_FILE.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            metric = (row.get("metric") or "").strip()
            value_str = (row.get("value") or "").strip()
            if not metric or metric.startswith("#") or not value_str:
                continue
            try:
                if "." not in value_str:
                    parsed[metric] = int(value_str)
                else:
                    parsed[metric] = float(value_str)
            except ValueError:
                parsed[metric] = value_str

    _results_cache = parsed
    return parsed


def metric_tolerance(metric, expected):
    if metric in EXACT_INT_METRICS:
        return 0
    if metric in ENTROPY_METRICS:
        return abs(expected) * ENTROPY_TOLERANCE
    if isinstance(expected, int) and expected > 1000:
        return expected * LARGE_INT_PERCENT_TOLERANCE
    return FLOAT_TOLERANCE


@pytest.mark.parametrize("metric", list(EXPECTED_VALUES.keys()))
def test_metric(metric):
    results = load_results()
    assert results is not None, "results file not found"
    assert metric in results, f"missing metric: {metric}"

    expected = EXPECTED_VALUES[metric]
    actual = results[metric]

    if metric in STRING_METRICS:
        assert actual == expected, f"{metric}: expected {expected}, got {actual}"
        return

    tolerance = metric_tolerance(metric, expected)
    assert abs(actual - expected) <= tolerance, (
        f"{metric}: expected {expected}, got {actual}, tolerance {tolerance}"
    )
