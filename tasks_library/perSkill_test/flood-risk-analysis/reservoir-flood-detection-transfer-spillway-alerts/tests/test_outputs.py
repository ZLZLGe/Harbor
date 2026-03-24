import json
import os


OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/root/output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "spillway_alerts.json")


EXPECTED = {
    "report_window": {
        "start_date": "2025-10-03",
        "end_date": "2025-10-07",
    },
    "summary": {
        "reservoirs_evaluated": 5,
        "reservoirs_with_flood_stage": 4,
    },
    "reservoir_alerts": [
        {
            "reservoir_id": "BRM-17",
            "reservoir_name": "Bramble Reservoir",
            "flood_risk_days": 5,
            "highest_severity": "major",
            "peak_day": "2025-10-06",
            "peak_level_ft": 61.2,
        },
        {
            "reservoir_id": "ALB-01",
            "reservoir_name": "Albright Reservoir",
            "flood_risk_days": 3,
            "highest_severity": "major",
            "peak_day": "2025-10-04",
            "peak_level_ft": 58.7,
        },
        {
            "reservoir_id": "FAL-31",
            "reservoir_name": "Falls Bend Reservoir",
            "flood_risk_days": 2,
            "highest_severity": "flood",
            "peak_day": "2025-10-07",
            "peak_level_ft": 54.0,
        },
        {
            "reservoir_id": "CDR-22",
            "reservoir_name": "Cedar Draw Reservoir",
            "flood_risk_days": 1,
            "highest_severity": "flood",
            "peak_day": "2025-10-05",
            "peak_level_ft": 48.6,
        },
    ],
}


def load_payload():
    with open(OUTPUT_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_output_file_exists():
    assert os.path.exists(OUTPUT_FILE), (
        f"JSON output not found at {OUTPUT_FILE}"
    )


def test_output_matches_expected_payload():
    payload = load_payload()
    assert payload == EXPECTED, f"Expected {EXPECTED}, got {payload}"


def test_action_only_non_roster_and_out_of_window_records_are_not_reported():
    payload = load_payload()
    reservoir_ids = [row["reservoir_id"] for row in payload["reservoir_alerts"]]

    assert "ELM-09" not in reservoir_ids
    assert "GRT-77" not in reservoir_ids
    assert payload["summary"]["reservoirs_evaluated"] == 5
    assert payload["summary"]["reservoirs_with_flood_stage"] == 4
