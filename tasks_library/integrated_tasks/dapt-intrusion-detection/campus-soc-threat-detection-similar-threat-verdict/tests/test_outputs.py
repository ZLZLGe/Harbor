import json
from pathlib import Path


OUTPUT_FILE = Path("/root/campus_verdict.json")

EXPECTED_TOP_LEVEL = {
    "capture_id",
    "verdict",
    "is_traffic_benign",
    "has_port_scan",
    "has_dos_pattern",
    "has_beaconing",
    "supporting_metrics",
}

EXPECTED_SUPPORTING = {
    "port_scan_source",
    "port_scan_unique_ports",
    "port_scan_dst_port_entropy",
    "port_scan_syn_only_ratio",
    "packets_per_minute_avg",
    "packets_per_minute_max",
    "dos_ratio",
    "iat_cv",
}


def load_output():
    assert OUTPUT_FILE.exists(), "Missing /root/campus_verdict.json"
    with OUTPUT_FILE.open() as handle:
        return json.load(handle)


def test_top_level_shape():
    data = load_output()
    assert set(data) == EXPECTED_TOP_LEVEL
    assert isinstance(data["supporting_metrics"], dict)
    assert set(data["supporting_metrics"]) == EXPECTED_SUPPORTING


def test_capture_identity_and_verdict():
    data = load_output()
    assert data["capture_id"] == "campus-west-quiet-hour-17"
    assert data["verdict"] == "malicious"
    assert data["is_traffic_benign"] is False


def test_threat_flags():
    data = load_output()
    assert data["has_port_scan"] is True
    assert data["has_dos_pattern"] is False
    assert data["has_beaconing"] is True


def test_supporting_metrics():
    data = load_output()
    metrics = data["supporting_metrics"]

    assert metrics["port_scan_source"] == "10.77.4.19"
    assert metrics["port_scan_unique_ports"] == 148
    assert metrics["port_scan_dst_port_entropy"] == 6.27
    assert metrics["port_scan_syn_only_ratio"] == 0.81
    assert metrics["packets_per_minute_avg"] == 312.5
    assert metrics["packets_per_minute_max"] == 4680
    assert abs(metrics["dos_ratio"] - 14.976) < 1e-9
    assert metrics["iat_cv"] == 0.42
