import json
from pathlib import Path


INPUT_FILE = Path("/root/capture_feature_matrix.json")
OUTPUT_FILE = Path("/root/capture_verdicts.json")


def compute_expected(record):
    has_port_scan = (
        record["port_entropy"] > 6.0
        and record["syn_only_ratio"] > 0.7
        and record["unique_ports"] > 100
    )

    avg = record["packets_per_minute_avg"]
    has_dos_pattern = False if avg == 0 else (record["packets_per_minute_max"] / avg) > 20
    has_beaconing = record["iat_cv"] < 0.5
    is_traffic_benign = not (has_port_scan or has_dos_pattern or has_beaconing)

    active = [
        name
        for name, enabled in (
            ("port_scan", has_port_scan),
            ("dos_pattern", has_dos_pattern),
            ("beaconing", has_beaconing),
        )
        if enabled
    ]
    if not active:
        dominant_risk = "benign"
    elif len(active) == 1:
        dominant_risk = active[0]
    else:
        dominant_risk = "multi_threat"

    return {
        "capture_id": record["capture_id"],
        "has_port_scan": has_port_scan,
        "has_dos_pattern": has_dos_pattern,
        "has_beaconing": has_beaconing,
        "is_traffic_benign": is_traffic_benign,
        "dominant_risk": dominant_risk,
    }


def load_json(path):
    with open(path, "r", encoding="utf-8") as infile:
        return json.load(infile)


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), "Missing /root/capture_verdicts.json"


def test_output_is_json_array():
    verdicts = load_json(OUTPUT_FILE)
    assert isinstance(verdicts, list), "Output must be a JSON array"


def test_verdicts_match_expected_contract():
    inputs = load_json(INPUT_FILE)
    verdicts = load_json(OUTPUT_FILE)

    assert len(verdicts) == len(inputs), "Output must contain one verdict per input capture"

    expected = [compute_expected(record) for record in inputs]

    for verdict, expected_verdict in zip(verdicts, expected):
        assert isinstance(verdict, dict), "Each verdict must be a JSON object"
        for required_key in expected_verdict:
            assert required_key in verdict, f"Missing key: {required_key}"

        assert verdict["capture_id"] == expected_verdict["capture_id"], (
            "Output order must match input order and preserve capture_id"
        )
        assert isinstance(verdict["has_port_scan"], bool), "has_port_scan must be a JSON boolean"
        assert isinstance(verdict["has_dos_pattern"], bool), "has_dos_pattern must be a JSON boolean"
        assert isinstance(verdict["has_beaconing"], bool), "has_beaconing must be a JSON boolean"
        assert isinstance(verdict["is_traffic_benign"], bool), (
            "is_traffic_benign must be a JSON boolean"
        )

        assert verdict["has_port_scan"] == expected_verdict["has_port_scan"]
        assert verdict["has_dos_pattern"] == expected_verdict["has_dos_pattern"]
        assert verdict["has_beaconing"] == expected_verdict["has_beaconing"]
        assert verdict["is_traffic_benign"] == expected_verdict["is_traffic_benign"]
        assert verdict["dominant_risk"] == expected_verdict["dominant_risk"]


def test_dominant_risk_is_consistent_with_flags():
    verdicts = load_json(OUTPUT_FILE)

    allowed_values = {"benign", "port_scan", "dos_pattern", "beaconing", "multi_threat"}
    for verdict in verdicts:
        assert verdict["dominant_risk"] in allowed_values

        flags = [
            verdict["has_port_scan"],
            verdict["has_dos_pattern"],
            verdict["has_beaconing"],
        ]
        active_count = sum(flags)

        if active_count == 0:
            assert verdict["is_traffic_benign"] is True
            assert verdict["dominant_risk"] == "benign"
        elif active_count == 1:
            assert verdict["is_traffic_benign"] is False
            mapping = {
                "has_port_scan": "port_scan",
                "has_dos_pattern": "dos_pattern",
                "has_beaconing": "beaconing",
            }
            for key, expected_risk in mapping.items():
                if verdict[key]:
                    assert verdict["dominant_risk"] == expected_risk
        else:
            assert verdict["is_traffic_benign"] is False
            assert verdict["dominant_risk"] == "multi_threat"
