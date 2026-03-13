import json
import math
import os
import unittest
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(
    os.environ.get("OUTPUT_FILE", "/root/ot_zone_risk_assessment.json")
)
LOCAL_FALLBACK = TASK_ROOT / ".tmp_ot_zone_risk_assessment.json"


def resolve_output_file():
    try:
        if DEFAULT_OUTPUT.exists():
            return DEFAULT_OUTPUT
    except PermissionError:
        pass
    return LOCAL_FALLBACK


RESULTS_FILE = resolve_output_file()
FLOAT_TOLERANCE = 1e-4

EXPECTED = {
    "capture_summary": {
        "total_packets": 372,
        "ip_packets": 364,
        "tcp_packets": 244,
        "udp_packets": 120,
        "arp_packets": 8,
        "internal_ip_packets": 316,
        "external_ip_packets": 48,
        "duration_seconds": 1410.3,
        "active_minutes": 24,
    },
    "baseline": {
        "controller_assets": ["plc-line-a", "plc-line-b"],
        "hmi_asset_id": "hmi-main",
        "engineering_asset_id": "eng-station-1",
        "controller_service_ports": [102, 502],
        "hmi_controller_pairs": 2,
        "engineering_controller_pairs": 2,
        "hmi_poll_median_interval_seconds": 10.0,
        "engineering_maintenance_median_interval_seconds": 300.0,
    },
    "entropy_profile": {
        "src_ip_entropy": 1.2155,
        "dst_ip_entropy": 1.8963,
        "dst_port_entropy": 4.9442,
        "eng_station_target_entropy": 1.3342,
        "eng_station_dst_port_entropy": 4.7279,
    },
    "cadence_profile": {
        "control_loop": {
            "src_asset_id": "hmi-main",
            "dst_asset_id": "plc-line-a",
            "dst_port": 502,
            "protocol": "TCP",
            "flow_packets": 12,
            "median_interval_seconds": 10.0,
            "interval_cv": 0.0,
        },
        "maintenance_loop": {
            "src_asset_id": "eng-station-1",
            "dst_asset_id": "plc-line-a",
            "dst_port": 102,
            "protocol": "TCP",
            "flow_packets": 5,
            "median_interval_seconds": 300.0,
            "interval_cv": 0.0,
        },
        "external_candidate": {
            "src_asset_id": "eng-station-1",
            "dst_ip": "198.51.100.77",
            "dst_port": 443,
            "protocol": "TCP",
            "flow_packets": 24,
            "median_interval_seconds": 60.0,
            "interval_cv": 0.0,
        },
    },
    "bidirectional_relationships": {
        "unique_internal_flows": 137,
        "bidirectional_internal_flow_pairs": 4,
        "controller_hmi_bidirectional_pairs": 2,
        "engineering_controller_bidirectional_pairs": 2,
        "unanswered_scan_flows": 128,
    },
    "risk_assessment": {
        "scan_source_asset_id": "eng-station-1",
        "scan_target_asset_id": "plc-line-a",
        "scan_unique_dst_ports": 130,
        "scan_dst_port_entropy": 6.9403,
        "scan_syn_only_ratio": 0.9275,
        "burst_source_asset_id": "eng-station-1",
        "burst_minute_index": 12,
        "burst_packets": 250,
        "burst_ratio": 21.2766,
        "beacon_asset_id": "eng-station-1",
        "beacon_dst_ip": "198.51.100.77",
        "beacon_dst_port": 443,
        "beacon_protocol": "TCP",
        "beacon_flow_packets": 24,
        "beacon_median_interval_seconds": 60.0,
        "beacon_interval_cv": 0.0,
        "has_scan": True,
        "has_flood_like": True,
        "has_beaconing": True,
        "is_ot_zone_stable": False,
    },
}


class TestOtZoneRiskAssessment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not RESULTS_FILE.exists():
            raise AssertionError(f"results file not found: {RESULTS_FILE}")
        cls.data = json.loads(RESULTS_FILE.read_text())

    def assert_json_matches(self, actual, expected, path="root"):
        self.assertEqual(type(actual), type(expected), f"type mismatch at {path}")

        if isinstance(expected, dict):
            self.assertEqual(
                set(actual.keys()),
                set(expected.keys()),
                f"key mismatch at {path}",
            )
            for key, expected_value in expected.items():
                self.assert_json_matches(actual[key], expected_value, f"{path}.{key}")
            return

        if isinstance(expected, list):
            self.assertEqual(actual, expected, f"list mismatch at {path}")
            return

        if isinstance(expected, float):
            self.assertTrue(
                math.isclose(actual, expected, rel_tol=0.0, abs_tol=FLOAT_TOLERANCE),
                f"float mismatch at {path}: expected {expected}, got {actual}",
            )
            return

        self.assertEqual(actual, expected, f"value mismatch at {path}")

    def test_top_level_schema(self):
        self.assertEqual(
            set(self.data.keys()),
            {
                "capture_summary",
                "baseline",
                "entropy_profile",
                "cadence_profile",
                "bidirectional_relationships",
                "risk_assessment",
            },
        )

    def test_expected_output(self):
        self.assert_json_matches(self.data, EXPECTED)

    def test_internal_consistency(self):
        summary = self.data["capture_summary"]
        baseline = self.data["baseline"]
        cadence = self.data["cadence_profile"]
        relationships = self.data["bidirectional_relationships"]
        risk = self.data["risk_assessment"]

        self.assertEqual(
            summary["internal_ip_packets"] + summary["external_ip_packets"],
            summary["ip_packets"],
            "internal + external IP packets must equal total IP packets",
        )
        self.assertEqual(
            relationships["bidirectional_internal_flow_pairs"],
            relationships["controller_hmi_bidirectional_pairs"]
            + relationships["engineering_controller_bidirectional_pairs"],
            "bidirectional pairs should be fully explained by HMI/controller and engineering/controller links in this capture",
        )
        self.assertEqual(
            baseline["controller_service_ports"],
            sorted(baseline["controller_service_ports"]),
            "controller service ports must be sorted",
        )
        self.assertEqual(
            risk["has_scan"],
            (
                risk["scan_unique_dst_ports"] > 100
                and risk["scan_dst_port_entropy"] > 6.0
                and risk["scan_syn_only_ratio"] > 0.7
            ),
            "scan flag must follow the documented threshold",
        )
        self.assertEqual(
            risk["has_flood_like"],
            risk["burst_ratio"] > 20 and risk["burst_packets"] >= 100,
            "flood flag must follow the documented threshold",
        )
        self.assertEqual(
            risk["has_beaconing"],
            20 <= risk["beacon_median_interval_seconds"] <= 90
            and risk["beacon_interval_cv"] < 0.15,
            "beacon flag must follow the documented threshold",
        )
        self.assertEqual(
            risk["is_ot_zone_stable"],
            not (
                risk["has_scan"]
                or risk["has_flood_like"]
                or risk["has_beaconing"]
            ),
            "overall stability must be derived from the three risk flags",
        )
        self.assertLess(
            cadence["control_loop"]["median_interval_seconds"],
            cadence["maintenance_loop"]["median_interval_seconds"],
            "control loop should be faster than engineering maintenance loop",
        )


if __name__ == "__main__":
    unittest.main()
