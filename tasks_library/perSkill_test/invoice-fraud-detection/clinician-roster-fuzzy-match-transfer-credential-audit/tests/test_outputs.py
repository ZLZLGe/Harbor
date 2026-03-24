import csv
import os


OUTPUT_PATH = os.environ.get("PRIMARY_OUTPUT_FILE", "/root/license_exceptions.csv")

EXPECTED_ROWS = [
    {
        "assignment_id": "A-004",
        "shift_date": "2026-03-19",
        "unit": "Clinic",
        "clinician_alias": "Tasha Harris",
        "reported_license_number": "LIC-9999",
        "matched_license_number": "LIC-4105",
        "matched_registry_name": "Tasha Renee Harris",
        "reason": "License Number Mismatch",
    },
    {
        "assignment_id": "A-005",
        "shift_date": "2026-03-20",
        "unit": "Emergency",
        "clinician_alias": "Dr Omar N Haddaad",
        "reported_license_number": "LIC-4106",
        "matched_license_number": "LIC-4106",
        "matched_registry_name": "Omar Nadim Haddad",
        "reason": "Credential Mismatch",
    },
    {
        "assignment_id": "A-006",
        "shift_date": "2026-03-20",
        "unit": "Respiratory",
        "clinician_alias": "L Thompson",
        "reported_license_number": "LIC-4107",
        "matched_license_number": "LIC-4107",
        "matched_registry_name": "Lena Thompson",
        "reason": "Inactive License",
    },
    {
        "assignment_id": "A-007",
        "shift_date": "2026-03-20",
        "unit": "Pediatrics",
        "clinician_alias": "Mika Rios",
        "reported_license_number": "LIC-4108",
        "matched_license_number": "LIC-4108",
        "matched_registry_name": "Mica Rios",
        "reason": "Expired License",
    },
    {
        "assignment_id": "A-010",
        "shift_date": "2026-03-20",
        "unit": "Telemetry",
        "clinician_alias": "M. Alvarez",
        "reported_license_number": "LIC-7777",
        "matched_license_number": "",
        "matched_registry_name": "",
        "reason": "Unresolved Clinician",
    },
]

CLEAN_ASSIGNMENT_IDS = {"A-001", "A-002", "A-003", "A-008", "A-009", "A-011"}
EXPECTED_HEADER = [
    "assignment_id",
    "shift_date",
    "unit",
    "clinician_alias",
    "reported_license_number",
    "matched_license_number",
    "matched_registry_name",
    "reason",
]


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists(OUTPUT_PATH)

    def test_exact_rows(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            actual_rows = list(reader)
            assert reader.fieldnames == EXPECTED_HEADER, f"Unexpected header: {reader.fieldnames}"

        assert actual_rows == EXPECTED_ROWS

    def test_clean_assignments_are_not_flagged(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            flagged_ids = {row["assignment_id"] for row in reader}

        assert not (flagged_ids & CLEAN_ASSIGNMENT_IDS), (
            f"Clean assignments were incorrectly flagged: {sorted(flagged_ids & CLEAN_ASSIGNMENT_IDS)}"
        )
