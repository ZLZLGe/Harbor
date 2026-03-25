import csv
import json
import re
from pathlib import Path

from unified_planning.io import PDDLReader
from unified_planning.shortcuts import PlanValidator


CONFIG_PATH = Path("/root/warehouse_batch.json")
SUMMARY_PATH = Path("/root/transfer1_warehouse_dispatch.csv")


def read_plan_lines(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.lstrip().startswith(";")]


def action_name(action_line: str):
    match = re.match(r"^\(?([A-Za-z0-9_-]+)", action_line.strip())
    assert match, f"Cannot parse action name from {action_line}"
    return match.group(1)


def validate_plan(domain_file: str, problem_file: str, plan_file: str):
    reader = PDDLReader()
    problem = reader.parse_problem(domain_file, problem_file)
    plan = reader.parse_plan(problem, plan_file)
    with PlanValidator(problem_kind=problem.kind, plan_kind=plan.kind) as validator:
        return validator.validate(problem, plan)


def test_outputs_exist_and_match_dispatch_csv():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    expected_cases = sorted(config["cases"], key=lambda item: item["case_id"])
    with open(SUMMARY_PATH, "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["case_id"] for row in rows] == [item["case_id"] for item in expected_cases]

    for case, row in zip(expected_cases, rows):
        plan_path = Path(case["plan_output"])
        assert plan_path.exists(), f"Missing plan file for {case['case_id']}"
        lines = read_plan_lines(plan_path)
        assert lines, f"Empty plan file for {case['case_id']}"
        assert row["plan_file"] == str(plan_path)
        assert int(row["steps"]) == len(lines)
        assert int(row["pick_actions"]) == sum(1 for line in lines if action_name(line) == "pick")
        assert int(row["drop_actions"]) == sum(1 for line in lines if action_name(line) == "drop")
        assert validate_plan(case["domain"], case["problem"], str(plan_path))
