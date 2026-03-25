import json
from pathlib import Path

from unified_planning.io import PDDLReader
from unified_planning.shortcuts import PlanValidator


CONFIG_PATH = Path("/root/lab_batch.json")
SUMMARY_PATH = Path("/root/transfer2_lab_runbook.md")


def read_plan_lines(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.lstrip().startswith(";")]


def validate_plan(domain_file: str, problem_file: str, plan_file: str):
    reader = PDDLReader()
    problem = reader.parse_problem(domain_file, problem_file)
    plan = reader.parse_plan(problem, plan_file)
    with PlanValidator(problem_kind=problem.kind, plan_kind=plan.kind) as validator:
        return validator.validate(problem, plan)


def parse_markdown_rows(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]

    assert lines[0] == "# Lab Runbook"
    assert lines[1] == ""
    assert lines[2] == "| case_id | plan_file | steps | terminal_action |"
    assert lines[3] == "| --- | --- | ---: | --- |"

    rows = []
    for line in lines[4:]:
        if not line.strip():
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        assert len(parts) == 4, f"Unexpected markdown row: {line}"
        rows.append(
            {
                "case_id": parts[0],
                "plan_file": parts[1],
                "steps": parts[2],
                "terminal_action": parts[3],
            }
        )
    return rows


def test_outputs_exist_and_match_runbook():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    expected_cases = sorted(config["cases"], key=lambda item: item["case_id"])
    rows = parse_markdown_rows(SUMMARY_PATH)
    assert [row["case_id"] for row in rows] == [item["case_id"] for item in expected_cases]

    for case, row in zip(expected_cases, rows):
        plan_path = Path(case["plan_output"])
        assert plan_path.exists(), f"Missing plan file for {case['case_id']}"
        lines = read_plan_lines(plan_path)
        assert lines, f"Empty plan file for {case['case_id']}"
        assert row["plan_file"] == str(plan_path)
        assert int(row["steps"]) == len(lines)
        assert row["terminal_action"] == lines[-1]
        assert validate_plan(case["domain"], case["problem"], str(plan_path))
