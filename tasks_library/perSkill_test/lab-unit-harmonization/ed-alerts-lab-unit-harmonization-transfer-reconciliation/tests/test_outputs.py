import json
import os
import re


OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/ed_alert_lab_reconciliation.json")
NUMERIC_PATTERN = re.compile(r"^-?\d+\.\d{2}$")

EXPECTED_REPORT = {
    "report_id": "ed-critical-lab-reconciliation",
    "target_tests": [
        {"test_code": "K", "standard_name": "Potassium", "standard_unit": "mEq/L"},
        {"test_code": "GLU", "standard_name": "Glucose", "standard_unit": "mg/dL"},
        {"test_code": "CREA", "standard_name": "Serum Creatinine", "standard_unit": "mg/dL"},
        {"test_code": "HGB", "standard_name": "Hemoglobin", "standard_unit": "g/dL"},
        {"test_code": "LAC", "standard_name": "Lactate", "standard_unit": "mmol/L"},
        {"test_code": "CA", "standard_name": "Calcium", "standard_unit": "mg/dL"},
    ],
    "encounters": [
        {
            "encounter_id": "ED-1001",
            "patient_id": "PT-100",
            "arrival_time": "2025-03-01T08:04:00",
            "had_unit_conversion": True,
            "standardized_results": [
                {
                    "record_id": "AL-001",
                    "test_code": "K",
                    "standard_name": "Potassium",
                    "standard_value": "6.20",
                    "standard_unit": "mEq/L",
                    "converted": False,
                },
                {
                    "record_id": "AL-002",
                    "test_code": "GLU",
                    "standard_name": "Glucose",
                    "standard_value": "120.72",
                    "standard_unit": "mg/dL",
                    "converted": True,
                },
                {
                    "record_id": "AL-003",
                    "test_code": "HGB",
                    "standard_name": "Hemoglobin",
                    "standard_value": "11.30",
                    "standard_unit": "g/dL",
                    "converted": True,
                },
                {
                    "record_id": "AL-004",
                    "test_code": "LAC",
                    "standard_name": "Lactate",
                    "standard_value": "2.00",
                    "standard_unit": "mmol/L",
                    "converted": True,
                },
            ],
            "excluded_records": [
                {"record_id": "AL-005", "test_code": "CREA", "reason": "missing_result_raw"},
            ],
        },
        {
            "encounter_id": "ED-1002",
            "patient_id": "PT-220",
            "arrival_time": "2025-03-01T08:17:00",
            "had_unit_conversion": True,
            "standardized_results": [
                {
                    "record_id": "AL-008",
                    "test_code": "K",
                    "standard_name": "Potassium",
                    "standard_value": "3.10",
                    "standard_unit": "mEq/L",
                    "converted": False,
                },
                {
                    "record_id": "AL-010",
                    "test_code": "GLU",
                    "standard_name": "Glucose",
                    "standard_value": "245.00",
                    "standard_unit": "mg/dL",
                    "converted": False,
                },
                {
                    "record_id": "AL-007",
                    "test_code": "CREA",
                    "standard_name": "Serum Creatinine",
                    "standard_value": "1.80",
                    "standard_unit": "mg/dL",
                    "converted": False,
                },
                {
                    "record_id": "AL-009",
                    "test_code": "LAC",
                    "standard_name": "Lactate",
                    "standard_value": "1.50",
                    "standard_unit": "mmol/L",
                    "converted": False,
                },
                {
                    "record_id": "AL-011",
                    "test_code": "CA",
                    "standard_name": "Calcium",
                    "standard_value": "10.20",
                    "standard_unit": "mg/dL",
                    "converted": True,
                },
            ],
            "excluded_records": [
                {"record_id": "AL-012", "test_code": "HGB", "reason": "missing_result_raw"},
            ],
        },
        {
            "encounter_id": "ED-1003",
            "patient_id": "PT-305",
            "arrival_time": "2025-03-01T09:02:00",
            "had_unit_conversion": True,
            "standardized_results": [
                {
                    "record_id": "AL-015",
                    "test_code": "K",
                    "standard_name": "Potassium",
                    "standard_value": "2.90",
                    "standard_unit": "mEq/L",
                    "converted": False,
                },
                {
                    "record_id": "AL-014",
                    "test_code": "GLU",
                    "standard_name": "Glucose",
                    "standard_value": "95.00",
                    "standard_unit": "mg/dL",
                    "converted": False,
                },
                {
                    "record_id": "AL-013",
                    "test_code": "CREA",
                    "standard_name": "Serum Creatinine",
                    "standard_value": "2.40",
                    "standard_unit": "mg/dL",
                    "converted": True,
                },
                {
                    "record_id": "AL-016",
                    "test_code": "HGB",
                    "standard_name": "Hemoglobin",
                    "standard_value": "10.40",
                    "standard_unit": "g/dL",
                    "converted": False,
                },
                {
                    "record_id": "AL-017",
                    "test_code": "LAC",
                    "standard_name": "Lactate",
                    "standard_value": "3.00",
                    "standard_unit": "mmol/L",
                    "converted": True,
                },
            ],
            "excluded_records": [],
        },
        {
            "encounter_id": "ED-1004",
            "patient_id": "PT-410",
            "arrival_time": "2025-03-01T09:20:00",
            "had_unit_conversion": False,
            "standardized_results": [
                {
                    "record_id": "AL-018",
                    "test_code": "CA",
                    "standard_name": "Calcium",
                    "standard_value": "8.80",
                    "standard_unit": "mg/dL",
                    "converted": False,
                },
            ],
            "excluded_records": [
                {"record_id": "AL-019", "test_code": "GLU", "reason": "missing_result_raw"},
                {"record_id": "AL-020", "test_code": "K", "reason": "missing_arrival_time"},
            ],
        },
    ],
}


def load_report():
    assert os.path.exists(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def test_report_is_valid_json():
    report = load_report()
    assert isinstance(report, dict)
    assert set(report.keys()) == {"report_id", "target_tests", "encounters"}


def test_numeric_strings_are_clean_and_fixed():
    report = load_report()
    for encounter in report["encounters"]:
        for result in encounter["standardized_results"]:
            value = result["standard_value"]
            assert NUMERIC_PATTERN.match(value)
            assert value == value.strip()
            assert "," not in value
            assert "e" not in value.lower()


def test_conversion_flags_match_results():
    report = load_report()
    expected_flags = {
        "ED-1001": True,
        "ED-1002": True,
        "ED-1003": True,
        "ED-1004": False,
    }
    actual_flags = {item["encounter_id"]: item["had_unit_conversion"] for item in report["encounters"]}
    assert actual_flags == expected_flags


def test_report_matches_expected_contract():
    report = load_report()
    assert report == EXPECTED_REPORT
