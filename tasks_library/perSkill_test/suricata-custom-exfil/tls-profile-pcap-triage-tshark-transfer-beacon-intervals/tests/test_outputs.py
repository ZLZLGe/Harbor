from __future__ import annotations

import json
import re
from pathlib import Path


INPUT_PATH = Path("/workspace/inputs/tls_handshake_mix.pcap")
OUTPUT_PATH = Path("/workspace/outputs/tls_beacon_profile.json")
EXPECTED = [
    {
        "client_ip": "10.77.0.21",
        "target_ip": "198.51.100.20",
        "target_port": 443,
        "sni": "api.sync-node.net",
        "connection_count": 6,
        "approx_period_seconds": 60,
    },
    {
        "client_ip": "10.77.0.44",
        "target_ip": "203.0.113.77",
        "target_port": 443,
        "sni": "edge-pulse.backhaul.org",
        "connection_count": 5,
        "approx_period_seconds": 90,
    },
]


def load_output() -> dict:
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    return json.loads(OUTPUT_PATH.read_text())


def test_input_pcap_exists():
    assert INPUT_PATH.exists(), f"missing input pcap: {INPUT_PATH}"


def test_output_has_beacons_array():
    data = load_output()
    assert isinstance(data, dict)
    assert "beacons" in data
    assert isinstance(data["beacons"], list)


def test_beacons_match_expected_groups_exactly():
    data = load_output()
    normalized = []
    for item in data["beacons"]:
        normalized.append(
            {
                "client_ip": item["client_ip"],
                "target_ip": item["target_ip"],
                "target_port": item["target_port"],
                "sni": item["sni"],
                "connection_count": item["connection_count"],
                "approx_period_seconds": item["approx_period_seconds"],
            }
        )
    assert normalized == EXPECTED


def test_beacons_are_sorted_by_required_key():
    data = load_output()
    keys = [
        (item["client_ip"], item["target_ip"], item["target_port"], item["sni"])
        for item in data["beacons"]
    ]
    assert keys == sorted(keys)


def test_each_beacon_uses_required_types_and_evidence():
    ip_re = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
    data = load_output()
    for item in data["beacons"]:
        assert isinstance(item["client_ip"], str)
        assert isinstance(item["target_ip"], str)
        assert isinstance(item["target_port"], int)
        assert isinstance(item["sni"], str)
        assert isinstance(item["connection_count"], int)
        assert isinstance(item["approx_period_seconds"], int)
        assert isinstance(item["evidence"], str)
        assert item["evidence"].strip()
        assert ip_re.fullmatch(item["client_ip"])
        assert ip_re.fullmatch(item["target_ip"])
        assert item["target_port"] > 0
        assert item["connection_count"] >= 5
        assert str(item["connection_count"]) in item["evidence"]
        assert str(item["approx_period_seconds"]) in item["evidence"]


def test_false_positive_groups_are_absent():
    data = load_output()
    seen = {
        (item["client_ip"], item["target_ip"], item["target_port"], item["sni"])
        for item in data["beacons"]
    }
    assert ("10.77.0.55", "203.0.113.88", 443, "portal.office.example") not in seen
    assert ("10.77.0.62", "198.51.100.60", 443, "status.mesh.example") not in seen
    assert ("10.77.0.70", "198.51.100.70", 443, "") not in seen
