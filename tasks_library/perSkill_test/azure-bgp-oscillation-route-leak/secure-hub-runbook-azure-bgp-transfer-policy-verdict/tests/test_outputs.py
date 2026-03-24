import json
import os
from pathlib import Path

import pytest


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
OUTPUT_FILE = OUTPUT_DIR / "secure_hub_runbook_verdict.json"


@pytest.fixture(scope="module")
def output_data():
    assert OUTPUT_FILE.exists(), f"Output file {OUTPUT_FILE} does not exist"
    return json.loads(OUTPUT_FILE.read_text())


def result_by_id(output_data):
    return {item["step_id"]: item for item in output_data["step_results"]}


class TestIncidentFindings:
    def test_output_structure(self, output_data):
        assert set(output_data.keys()) == {
            "incident_findings",
            "step_results",
            "execution_recommendation",
        }

    def test_incident_summary(self, output_data):
        assert output_data["incident_findings"] == {
            "oscillation_detected": True,
            "preference_cycle": [65412, 65413],
            "route_leak_detected": True,
            "route_leak_ids": ["obs-401"],
        }

    def test_step_order(self, output_data):
        assert [item["step_id"] for item in output_data["step_results"]] == [
            "rb-01",
            "rb-02",
            "rb-03",
            "rb-04",
            "rb-05",
            "rb-06",
            "rb-07",
            "rb-08",
        ]


class TestRunbookVerdicts:
    EXPECTED = {
        "rb-01": {
            "azure_allowed": False,
            "breaks_preference_cycle": False,
            "blocks_route_leak": False,
            "verdict": "prohibited",
        },
        "rb-02": {
            "azure_allowed": False,
            "breaks_preference_cycle": False,
            "blocks_route_leak": False,
            "verdict": "prohibited",
        },
        "rb-03": {
            "azure_allowed": True,
            "breaks_preference_cycle": True,
            "blocks_route_leak": False,
            "verdict": "cycle_only",
        },
        "rb-04": {
            "azure_allowed": True,
            "breaks_preference_cycle": False,
            "blocks_route_leak": True,
            "verdict": "leak_only",
        },
        "rb-05": {
            "azure_allowed": False,
            "breaks_preference_cycle": False,
            "blocks_route_leak": False,
            "verdict": "prohibited",
        },
        "rb-06": {
            "azure_allowed": True,
            "breaks_preference_cycle": True,
            "blocks_route_leak": True,
            "verdict": "full_fix",
        },
        "rb-07": {
            "azure_allowed": True,
            "breaks_preference_cycle": False,
            "blocks_route_leak": False,
            "verdict": "no_effect",
        },
        "rb-08": {
            "azure_allowed": True,
            "breaks_preference_cycle": False,
            "blocks_route_leak": True,
            "verdict": "leak_only",
        },
    }

    @pytest.mark.parametrize("step_id", sorted(EXPECTED))
    def test_step_values(self, output_data, step_id):
        results = result_by_id(output_data)
        assert step_id in results
        step = results[step_id]
        assert step["title"]
        for field, expected_value in self.EXPECTED[step_id].items():
            assert step[field] == expected_value


class TestExecutionRecommendation:
    def test_recommendation(self, output_data):
        assert output_data["execution_recommendation"] == {
            "preferred_step_ids": ["rb-06"],
            "fallback_step_sets": [["rb-03", "rb-04"], ["rb-03", "rb-08"]],
            "avoid_step_ids": ["rb-01", "rb-02", "rb-05", "rb-07"],
            "verdict": "prefer_single_allowed_full_fix",
        }

    def test_only_one_full_fix(self, output_data):
        results = output_data["step_results"]
        assert [item["step_id"] for item in results if item["verdict"] == "full_fix"] == ["rb-06"]
