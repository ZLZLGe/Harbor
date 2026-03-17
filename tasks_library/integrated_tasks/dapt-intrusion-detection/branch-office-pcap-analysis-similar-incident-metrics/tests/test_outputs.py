import csv
from pathlib import Path


RESULTS_FILE = Path("/root/branch_incident_metrics.csv")

ABS_TOL = 0.01

EXPECTED = {
    "protocol_tcp": 330,
    "protocol_udp": 1260,
    "protocol_icmp": 60,
    "protocol_arp": 60,
    "protocol_ip_total": 1650,
    "duration_seconds": 1852.96,
    "packets_per_minute_avg": 55.16,
    "packets_per_minute_max": 1350,
    "packets_per_minute_min": 12,
    "total_bytes": 88680,
    "avg_packet_size": 51.86,
    "min_packet_size": 42,
    "max_packet_size": 54,
    "src_ip_entropy": 1.5770,
    "dst_ip_entropy": 1.5907,
    "src_port_entropy": 7.5760,
    "dst_port_entropy": 2.3766,
    "unique_src_ports": 343,
    "unique_dst_ports": 244,
    "num_nodes": 11,
    "num_edges": 10,
    "network_density": 0.090909,
    "max_outdegree": 2,
    "max_indegree": 2,
    "iat_mean": 1.084236,
    "iat_variance": 53.556220,
    "iat_cv": 6.7496,
    "num_producers": 4,
    "num_consumers": 4,
    "unique_flows": 430,
    "tcp_flows": 270,
    "udp_flows": 160,
    "bidirectional_flows": 90,
    "is_traffic_benign": "false",
    "has_port_scan": "true",
    "has_dos_pattern": "true",
    "has_beaconing": "false",
}

EXACT_INT = {
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
    "max_outdegree",
    "max_indegree",
    "num_producers",
    "num_consumers",
    "unique_flows",
    "tcp_flows",
    "udp_flows",
    "bidirectional_flows",
}

STRING_METRICS = {
    "is_traffic_benign",
    "has_port_scan",
    "has_dos_pattern",
    "has_beaconing",
}


def load_results():
    assert RESULTS_FILE.exists(), f"missing output file: {RESULTS_FILE}"
    results = {}
    with RESULTS_FILE.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metric = (row.get("metric") or "").strip()
            value = (row.get("value") or "").strip()
            if not metric or metric.startswith("#"):
                continue
            assert value != "", f"metric {metric} has empty value"
            if metric in STRING_METRICS:
                results[metric] = value
            elif metric in EXACT_INT:
                results[metric] = int(value)
            else:
                results[metric] = float(value)
    return results


def test_expected_metrics_present():
    results = load_results()
    assert set(EXPECTED).issubset(results), f"missing metrics: {sorted(set(EXPECTED) - set(results))}"


def test_exact_integer_metrics():
    results = load_results()
    for metric in EXACT_INT:
        assert results[metric] == EXPECTED[metric], f"{metric}: expected {EXPECTED[metric]}, got {results[metric]}"


def test_float_metrics():
    results = load_results()
    for metric, expected in EXPECTED.items():
        if metric in EXACT_INT or metric in STRING_METRICS:
            continue
        actual = results[metric]
        assert abs(actual - expected) <= ABS_TOL, f"{metric}: expected {expected}, got {actual}"


def test_boolean_metrics():
    results = load_results()
    for metric in STRING_METRICS:
        assert results[metric] == EXPECTED[metric], f"{metric}: expected {EXPECTED[metric]}, got {results[metric]}"
