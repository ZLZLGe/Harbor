import json
import os
from pathlib import Path

import pytest


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
OUTPUT_FILE = OUTPUT_DIR / "multi_hub_remediation_matrix.json"


@pytest.fixture(scope="module")
def output_data():
    assert OUTPUT_FILE.exists(), f"Output file {OUTPUT_FILE} does not exist"
    return json.loads(OUTPUT_FILE.read_text())


def matrix_by_id(output_data):
    return {item["candidate_id"]: item for item in output_data["remediation_matrix"]}


class TestSummary:
    def test_output_structure(self, output_data):
        assert set(output_data.keys()) == {"analysis_summary", "remediation_matrix"}
        assert isinstance(output_data["remediation_matrix"], list)

    def test_analysis_summary(self, output_data):
        summary = output_data["analysis_summary"]
        assert summary["oscillation_detected"] is True
        assert summary["preference_cycle"] == [65102, 65103, 65104]
        assert summary["leak_ids"] == ["leak-001", "leak-002"]
        assert summary["affected_prefixes"] == ["10.44.10.0/24", "10.55.20.0/24"]

    def test_all_candidates_present_and_sorted(self, output_data):
        matrix = output_data["remediation_matrix"]
        candidate_ids = [item["candidate_id"] for item in matrix]
        assert candidate_ids == [
            "chg-01",
            "chg-02",
            "chg-03",
            "chg-04",
            "chg-05",
            "chg-06",
            "chg-07",
            "chg-08",
            "chg-09",
            "chg-10",
        ]


class TestMatrixEvaluation:
    EXPECTED = {
        "chg-01": {
            "azure_viable": False,
            "breaks_preference_cycle": False,
            "resolved_leak_ids": [],
            "remaining_leak_ids": ["leak-001", "leak-002"],
            "overall_effect": "no_fix",
        },
        "chg-02": {
            "azure_viable": True,
            "breaks_preference_cycle": True,
            "resolved_leak_ids": [],
            "remaining_leak_ids": ["leak-001", "leak-002"],
            "overall_effect": "cycle_only",
        },
        "chg-03": {
            "azure_viable": True,
            "breaks_preference_cycle": False,
            "resolved_leak_ids": ["leak-001"],
            "remaining_leak_ids": ["leak-002"],
            "overall_effect": "partial_leak_fix",
        },
        "chg-04": {
            "azure_viable": True,
            "breaks_preference_cycle": False,
            "resolved_leak_ids": ["leak-002"],
            "remaining_leak_ids": ["leak-001"],
            "overall_effect": "partial_leak_fix",
        },
        "chg-05": {
            "azure_viable": True,
            "breaks_preference_cycle": False,
            "resolved_leak_ids": ["leak-001", "leak-002"],
            "remaining_leak_ids": [],
            "overall_effect": "all_leaks_only",
        },
        "chg-06": {
            "azure_viable": True,
            "breaks_preference_cycle": True,
            "resolved_leak_ids": ["leak-001", "leak-002"],
            "remaining_leak_ids": [],
            "overall_effect": "full_fix",
        },
        "chg-07": {
            "azure_viable": True,
            "breaks_preference_cycle": True,
            "resolved_leak_ids": ["leak-001", "leak-002"],
            "remaining_leak_ids": [],
            "overall_effect": "full_fix",
        },
        "chg-08": {
            "azure_viable": False,
            "breaks_preference_cycle": False,
            "resolved_leak_ids": [],
            "remaining_leak_ids": ["leak-001", "leak-002"],
            "overall_effect": "prohibited",
        },
        "chg-09": {
            "azure_viable": True,
            "breaks_preference_cycle": True,
            "resolved_leak_ids": [],
            "remaining_leak_ids": ["leak-001", "leak-002"],
            "overall_effect": "cycle_only",
        },
        "chg-10": {
            "azure_viable": False,
            "breaks_preference_cycle": False,
            "resolved_leak_ids": [],
            "remaining_leak_ids": ["leak-001", "leak-002"],
            "overall_effect": "no_fix",
        },
    }

    @pytest.mark.parametrize("candidate_id", sorted(EXPECTED))
    def test_candidate_results(self, output_data, candidate_id):
        matrix = matrix_by_id(output_data)
        assert candidate_id in matrix
        item = matrix[candidate_id]
        assert item["candidate_change"]
        for field, expected_value in self.EXPECTED[candidate_id].items():
            assert item[field] == expected_value

    def test_only_two_full_fixes(self, output_data):
        matrix = output_data["remediation_matrix"]
        full_fix_ids = [item["candidate_id"] for item in matrix if item["overall_effect"] == "full_fix"]
        assert full_fix_ids == ["chg-06", "chg-07"]
