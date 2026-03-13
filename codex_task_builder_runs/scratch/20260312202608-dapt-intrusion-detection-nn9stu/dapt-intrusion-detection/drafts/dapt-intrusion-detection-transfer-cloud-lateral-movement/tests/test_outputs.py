import csv
import math
import os
import unittest
from pathlib import Path


RESULTS_FILE = Path(os.environ.get("OUTPUT_FILE", "/root/cloud_lateral_report.csv"))

EXPECTED = {
    "total_packets": 906,
    "total_bytes": 48930,
    "protocol_tcp": 226,
    "protocol_udp": 680,
    "protocol_ip_total": 906,
    "dominant_protocol": "udp",
    "duration_seconds": 1768.25,
    "packets_per_minute_avg": 30.2,
    "packets_per_minute_max": 624,
    "packets_per_minute_min": 2,
    "burst_minute_index": 18,
    "burst_ratio": 20.6623,
    "num_subnets": 4,
    "subnet_edges": 11,
    "subnet_graph_density": 0.916667,
    "max_host_fanout_ip": "10.10.1.5",
    "max_host_fanout": 7,
    "unique_flows": 268,
    "tcp_flows": 226,
    "udp_flows": 42,
    "bidirectional_flows": 40,
    "flow_diversity_ratio": 0.2958,
    "scan_source_ip": "10.10.3.60",
    "scan_unique_dst_ports": 128,
    "scan_syn_ratio": 1.0,
    "scan_dst_port_entropy": 7.0,
    "c2_src_ip": "10.10.3.15",
    "c2_dst_ip": "10.10.4.25",
    "c2_dst_port": 443,
    "c2_protocol": "TCP",
    "c2_flow_packets": 20,
    "c2_median_interval_seconds": 45.0,
    "c2_interval_cv": 0.0,
    "has_lateral_scan": "true",
    "has_dos_burst": "true",
    "has_periodic_c2": "true",
    "is_east_west_benign": "false",
}

EXACT_INT_METRICS = {
    "total_packets",
    "total_bytes",
    "protocol_tcp",
    "protocol_udp",
    "protocol_ip_total",
    "packets_per_minute_max",
    "packets_per_minute_min",
    "burst_minute_index",
    "num_subnets",
    "subnet_edges",
    "max_host_fanout",
    "unique_flows",
    "tcp_flows",
    "udp_flows",
    "bidirectional_flows",
    "scan_unique_dst_ports",
    "c2_dst_port",
    "c2_flow_packets",
}

TWO_DECIMAL_METRICS = {
    "duration_seconds",
    "packets_per_minute_avg",
}

FOUR_DECIMAL_METRICS = {
    "burst_ratio",
    "flow_diversity_ratio",
    "scan_syn_ratio",
    "scan_dst_port_entropy",
    "c2_median_interval_seconds",
    "c2_interval_cv",
}

SIX_DECIMAL_METRICS = {
    "subnet_graph_density",
}

STRING_METRICS = {
    "dominant_protocol",
    "max_host_fanout_ip",
    "scan_source_ip",
    "c2_src_ip",
    "c2_dst_ip",
    "c2_protocol",
    "has_lateral_scan",
    "has_dos_burst",
    "has_periodic_c2",
    "is_east_west_benign",
}


def load_results():
    if not RESULTS_FILE.exists():
        raise AssertionError(f"results file not found: {RESULTS_FILE}")

    parsed = {}
    with RESULTS_FILE.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            metric = (row.get("metric") or "").strip()
            value = (row.get("value") or "").strip()
            if not metric or metric.startswith("#") or not value:
                continue
            try:
                if "." not in value:
                    parsed[metric] = int(value)
                else:
                    parsed[metric] = float(value)
            except ValueError:
                parsed[metric] = value
    return parsed


def tolerance_for(metric):
    if metric in EXACT_INT_METRICS:
        return 0
    if metric in SIX_DECIMAL_METRICS:
        return 1e-6
    if metric in FOUR_DECIMAL_METRICS:
        return 1e-4
    if metric in TWO_DECIMAL_METRICS:
        return 1e-2
    return 1e-4


class TestCloudLateralReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = load_results()

    def test_expected_metrics(self):
        for metric, expected in EXPECTED.items():
            self.assertIn(metric, self.results, f"missing metric: {metric}")
            actual = self.results[metric]
            if metric in STRING_METRICS:
                self.assertEqual(actual, expected, f"{metric}: expected {expected}, got {actual}")
                continue
            self.assertTrue(
                math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance_for(metric)),
                f"{metric}: expected {expected}, got {actual}",
            )

    def test_internal_consistency(self):
        ratio = self.results["packets_per_minute_max"] / self.results["packets_per_minute_avg"]
        self.assertTrue(
            math.isclose(ratio, self.results["burst_ratio"], rel_tol=0.0, abs_tol=1e-4),
            "burst_ratio must equal max / avg",
        )
        self.assertEqual(
            self.results["has_dos_burst"],
            "true" if self.results["burst_ratio"] > 20 else "false",
            "has_dos_burst must follow the documented threshold",
        )
        benign = not (
            self.results["has_lateral_scan"] == "true"
            or self.results["has_dos_burst"] == "true"
            or self.results["has_periodic_c2"] == "true"
        )
        self.assertEqual(
            self.results["is_east_west_benign"],
            "true" if benign else "false",
            "is_east_west_benign must be derived from the three threat flags",
        )


if __name__ == "__main__":
    unittest.main()
