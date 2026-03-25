import json
import os
import re

from unified_planning.engines import SequentialPlanValidator
from unified_planning.io import PDDLReader
from unified_planning.plans import SequentialPlan
from unified_planning.shortcuts import OneshotPlanner


APP_DIR = "/app"
MANIFEST_PATH = "/app/runbooks/incidents.json"
RESULT_PATH = "/app/results/incident-runbooks.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_plan(problem, plan_path):
    with open(plan_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle.readlines()]

    assert lines, f"{plan_path} is empty"
    assert all(lines), f"{plan_path} contains blank lines"

    pattern = re.compile(r"^([A-Za-z0-9_-]+)\((.*)\)$")
    action_instances = []

    for lineno, line in enumerate(lines, start=1):
        match = pattern.fullmatch(line)
        assert match, f"{plan_path}:{lineno} is not a single action: {line}"
        action_name, raw_args = match.groups()

        try:
            action = problem.action(action_name)
        except Exception as exc:  # pragma: no cover
            raise AssertionError(f"{plan_path}:{lineno} unknown action {action_name}") from exc

        args = []
        if raw_args.strip():
            args = [part.strip() for part in raw_args.split(",")]
            assert all(args), f"{plan_path}:{lineno} has empty arguments"

        objects = []
        for arg_name in args:
            try:
                obj = problem.object(arg_name)
            except Exception as exc:  # pragma: no cover
                raise AssertionError(f"{plan_path}:{lineno} unknown object {arg_name}") from exc
            objects.append(obj)

        action_instances.append(action(*objects))

    return lines, SequentialPlan(action_instances)


def solve_problem(domain_file, problem_file):
    reader = PDDLReader()
    problem = reader.parse_problem(domain_file, problem_file)
    with OneshotPlanner(name="pyperplan") as planner:
        result = planner.solve(problem)
    return problem, result.plan


def test_incident_runbook_report():
    manifest = load_json(MANIFEST_PATH)
    report = load_json(RESULT_PATH)

    assert isinstance(report, dict), "incident-runbooks.json must be a JSON object"
    assert "incidents" in report, "incident-runbooks.json must contain incidents"
    assert isinstance(report["incidents"], list), "incidents must be a list"
    assert len(report["incidents"]) == len(manifest["incidents"]) == 5

    manifest_by_id = {item["incident_id"]: item for item in manifest["incidents"]}
    report_by_id = {item["incident_id"]: item for item in report["incidents"]}

    assert set(report_by_id) == set(manifest_by_id), "incident_id set does not match manifest"

    domain_file = os.path.join(APP_DIR, manifest["domain"])
    validator = SequentialPlanValidator()

    for incident_id, manifest_item in manifest_by_id.items():
        report_item = report_by_id[incident_id]
        assert report_item["status"] in {"solved", "unsolved"}, f"{incident_id}: invalid status"

        problem_file = os.path.join(APP_DIR, manifest_item["problem"])
        problem, expected_plan = solve_problem(domain_file, problem_file)

        if expected_plan is None:
            assert report_item["status"] == "unsolved", f"{incident_id}: should be unsolved"
            assert report_item["actions"] == [], f"{incident_id}: unsolved actions must be empty"
            assert report_item["action_count"] == 0, f"{incident_id}: unsolved action_count must be 0"
            assert report_item["plan_file"] is None, f"{incident_id}: unsolved plan_file must be null"

            output_path = os.path.join(APP_DIR, manifest_item["plan_output"])
            assert not os.path.exists(output_path), f"{incident_id}: unsolved incident must not create a plan file"
            continue

        assert report_item["status"] == "solved", f"{incident_id}: should be solved"
        assert report_item["plan_file"] == manifest_item["plan_output"], f"{incident_id}: unexpected plan_file"
        assert isinstance(report_item["actions"], list), f"{incident_id}: actions must be a list"
        assert report_item["action_count"] == len(report_item["actions"]), f"{incident_id}: action_count mismatch"

        output_path = os.path.join(APP_DIR, report_item["plan_file"])
        assert os.path.exists(output_path), f"{incident_id}: missing plan file"

        lines, plan = parse_plan(problem, output_path)
        assert report_item["actions"] == lines, f"{incident_id}: actions must match plan file"
        assert report_item["action_count"] == len(lines), f"{incident_id}: action_count must match plan lines"

        validation = validator.validate(problem, plan)
        assert validation.status.name == "VALID", f"{incident_id}: plan is not valid"
