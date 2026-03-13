import json
import math
import os
import unittest
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(os.environ.get("OUTPUT_FILE", "/root/iot_beacon_findings.json"))
LOCAL_FALLBACK = TASK_ROOT / ".tmp_iot_beacon_findings.json"


def resolve_output_file():
    try:
        if DEFAULT_OUTPUT.exists():
            return DEFAULT_OUTPUT
    except PermissionError:
        pass
    return LOCAL_FALLBACK


RESULTS_FILE = resolve_output_file()

EXPECTED = {
    "capture_summary": {
        "total_packets": 429,
        "ip_packets": 354,
        "tcp_packets": 200,
        "udp_packets": 154,
        "arp_packets": 75,
        "broadcast_packets": 195,
        "external_packets": 28,
        "packets_per_minute_avg": 61.2857,
        "packets_per_minute_max": 176,
        "peak_to_avg_ratio": 2.8718,
    },
    "broadcast_noise": {
        "device_id": "speaker-atrium",
        "ip": "10.42.0.21",
        "mac": "02:42:00:00:00:21",
        "broadcast_packets": 138,
        "broadcast_share": 0.7077,
        "top_channels": ["mdns", "ssdp", "arp"],
        "classification": "broadcast-noise",
    },
    "service_diffusion": {
        "device_id": "controller-core",
        "ip": "10.42.0.2",
        "unique_internal_targets": 7,
        "unique_dst_ports": 8,
        "dst_port_entropy": 2.9965,
        "classification": "controller-fanout",
    },
    "beaconing": {
        "device_id": "camera-lobby",
        "src_ip": "10.42.0.10",
        "dst_ip": "44.55.66.77",
        "dst_port": 443,
        "protocol": "TCP",
        "flow_packets": 12,
        "median_interval_seconds": 30.0,
        "interval_cv": 0.0,
        "classification": "periodic-beacon",
    },
    "scan": {
        "device_id": "thermostat-hvac-7f",
        "src_ip": "10.42.0.55",
        "target_ip": "10.42.0.2",
        "unique_dst_ports": 128,
        "dst_port_entropy": 7.0,
        "syn_only_ratio": 1.0,
        "classification": "scan",
    },
    "verdict": {
        "has_beaconing": True,
        "has_scan": True,
        "has_flood_like": False,
        "is_noise_only": False,
    },
}

FLOAT_TOLERANCE = 1e-4


class TestIotBeaconFindings(unittest.TestCase):
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
                "broadcast_noise",
                "service_diffusion",
                "beaconing",
                "scan",
                "verdict",
            },
        )

    def test_capture_summary(self):
        self.assert_json_matches(self.data["capture_summary"], EXPECTED["capture_summary"])

    def test_broadcast_noise(self):
        self.assert_json_matches(self.data["broadcast_noise"], EXPECTED["broadcast_noise"])

    def test_service_diffusion(self):
        self.assert_json_matches(
            self.data["service_diffusion"], EXPECTED["service_diffusion"]
        )

    def test_beaconing(self):
        self.assert_json_matches(self.data["beaconing"], EXPECTED["beaconing"])

    def test_scan(self):
        self.assert_json_matches(self.data["scan"], EXPECTED["scan"])

    def test_verdict(self):
        self.assert_json_matches(self.data["verdict"], EXPECTED["verdict"])

    def test_internal_consistency(self):
        summary = self.data["capture_summary"]
        broadcast = self.data["broadcast_noise"]
        verdict = self.data["verdict"]

        self.assertLessEqual(
            broadcast["broadcast_packets"],
            summary["broadcast_packets"],
            "device broadcast count cannot exceed total broadcast count",
        )
        self.assertEqual(
            verdict["has_flood_like"],
            summary["peak_to_avg_ratio"] > 20,
            "flood verdict must follow the documented threshold",
        )
        self.assertEqual(
            verdict["is_noise_only"],
            not (
                verdict["has_beaconing"]
                or verdict["has_scan"]
                or verdict["has_flood_like"]
            ),
            "noise-only verdict must be derived from the three threat booleans",
        )


if __name__ == "__main__":
    unittest.main()
