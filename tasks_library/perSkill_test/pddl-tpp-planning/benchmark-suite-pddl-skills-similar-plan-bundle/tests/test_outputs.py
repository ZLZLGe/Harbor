import json
import os
import re

from unified_planning.engines import SequentialPlanValidator
from unified_planning.io import PDDLReader
from unified_planning.plans import SequentialPlan


APP_DIR = "/app"
MANIFEST_PATH = "/app/benchmark/manifest.json"
INDEX_PATH = "/app/results/benchmark-plan-index.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_plan(problem, plan_path):
    with open(plan_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle.readlines()]

    assert lines, f"{plan_path} is empty"
    assert all(lines), f"{plan_path} contains blank lines"

    action_instances = []
    pattern = re.compile(r"^([A-Za-z0-9_-]+)\((.*)\)$")

    for lineno, line in enumerate(lines, start=1):
        match = pattern.fullmatch(line)
        assert match, f"{plan_path}:{lineno} is not a single action: {line}"
        action_name, raw_args = match.groups()

        try:
            action = problem.action(action_name)
        except Exception as exc:  # pragma: no cover - unified_planning raises its own error type
            raise AssertionError(f"{plan_path}:{lineno} unknown action {action_name}") from exc
        assert action is not None, f"{plan_path}:{lineno} unknown action {action_name}"

        arg_names = []
        if raw_args.strip():
            arg_names = [part.strip() for part in raw_args.split(",")]
            assert all(arg_names), f"{plan_path}:{lineno} has empty arguments"

        objects = []
        for arg_name in arg_names:
            try:
                obj = problem.object(arg_name)
            except Exception as exc:  # pragma: no cover
                raise AssertionError(f"{plan_path}:{lineno} unknown object {arg_name}") from exc
            assert obj is not None, f"{plan_path}:{lineno} unknown object {arg_name}"
            objects.append(obj)

        action_instances.append(action(*objects))

    return lines, SequentialPlan(action_instances)


def validate_index():
    manifest = load_json(MANIFEST_PATH)
    index = load_json(INDEX_PATH)

    assert isinstance(index, dict), "benchmark-plan-index.json must be a JSON object"
    assert "cases" in index, "benchmark-plan-index.json must contain a cases array"
    assert isinstance(index["cases"], list), "cases must be a list"
    assert len(index["cases"]) == len(manifest["cases"]) == 6

    manifest_by_id = {case["case_id"]: case for case in manifest["cases"]}
    index_by_id = {case["case_id"]: case for case in index["cases"]}

    assert set(index_by_id) == set(manifest_by_id), "case_id set does not match manifest"

    reader = PDDLReader()
    domain_file = os.path.join(APP_DIR, manifest["shared_domain"])

    for case_id, manifest_case in manifest_by_id.items():
        index_case = index_by_id[case_id]

        assert index_case["plan_file"] == manifest_case["plan_path"], f"{case_id}: unexpected plan_file"
        assert index_case["validated"] is True, f"{case_id}: validated must be true"

        plan_file = os.path.join(APP_DIR, index_case["plan_file"])
        problem_file = os.path.join(APP_DIR, manifest_case["problem"])

        assert os.path.exists(plan_file), f"{case_id}: missing plan file {plan_file}"

        problem = reader.parse_problem(domain_file, problem_file)
        lines, plan = parse_plan(problem, plan_file)

        assert index_case["step_count"] == len(lines), f"{case_id}: step_count mismatch"

        result = SequentialPlanValidator().validate(problem, plan)
        assert result.status.name == "VALID", f"{case_id}: plan is not valid"


def test_bundle_outputs():
    validate_index()
