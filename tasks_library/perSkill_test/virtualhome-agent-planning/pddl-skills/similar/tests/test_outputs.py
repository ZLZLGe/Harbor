import json
from pathlib import Path

from unified_planning.io import PDDLReader
from unified_planning.shortcuts import PlanValidator


CONFIG_PATH = Path("/root/airport_batch.json")
SUMMARY_PATH = Path("/root/similar_airport_manifest.json")


def read_plan_lines(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.lstrip().startswith(";")]


def validate_plan(domain_file: str, problem_file: str, plan_file: str):
    reader = PDDLReader()
    problem = reader.parse_problem(domain_file, problem_file)
    plan = reader.parse_plan(problem, plan_file)
    with PlanValidator(problem_kind=problem.kind, plan_kind=plan.kind) as validator:
        return validator.validate(problem, plan)


def test_outputs_exist_and_match_manifest():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    with open(SUMMARY_PATH, "r", encoding="utf-8") as handle:
        summary = json.load(handle)

    assert summary["scenario"] == "airport_dispatch"

    expected_cases = sorted(config["cases"], key=lambda item: item["case_id"])
    manifest_cases = summary["cases"]
    assert [item["case_id"] for item in manifest_cases] == [item["case_id"] for item in expected_cases]

    for case, manifest_entry in zip(expected_cases, manifest_cases):
        plan_path = Path(case["plan_output"])
        assert plan_path.exists(), f"Missing plan file for {case['case_id']}"
        lines = read_plan_lines(plan_path)
        assert lines, f"Empty plan file for {case['case_id']}"
        assert manifest_entry["plan_file"] == str(plan_path)
        assert manifest_entry["action_count"] == len(lines)
        assert manifest_entry["first_action"] == lines[0]
        assert manifest_entry["last_action"] == lines[-1]
        assert validate_plan(case["domain"], case["problem"], str(plan_path))
