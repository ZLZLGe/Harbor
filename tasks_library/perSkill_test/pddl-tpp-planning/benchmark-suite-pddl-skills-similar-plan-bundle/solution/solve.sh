#!/bin/bash

set -euo pipefail

mkdir -p /app/results/plans

python3 <<'PY'
import json
import os

from unified_planning.engines import SequentialPlanValidator
from unified_planning.io import PDDLReader
from unified_planning.shortcuts import OneshotPlanner


manifest_path = "/app/benchmark/manifest.json"
index_path = "/app/results/benchmark-plan-index.json"

with open(manifest_path, "r", encoding="utf-8") as handle:
    manifest = json.load(handle)

domain_file = os.path.join("/app", manifest["shared_domain"])
reader = PDDLReader()
index_cases = []

for case in manifest["cases"]:
    case_id = case["case_id"]
    problem_file = os.path.join("/app", case["problem"])
    plan_rel = case["plan_path"]
    plan_file = os.path.join("/app", plan_rel)
    os.makedirs(os.path.dirname(plan_file), exist_ok=True)

    problem = reader.parse_problem(domain_file, problem_file)
    with OneshotPlanner(name="pyperplan") as planner:
        result = planner.solve(problem)

    if result.plan is None:
        raise RuntimeError(f"{case_id}: planner did not return a plan")

    plan = result.plan
    validation = SequentialPlanValidator().validate(problem, plan)
    if validation.status.name != "VALID":
        raise RuntimeError(f"{case_id}: generated plan is not valid")

    with open(plan_file, "w", encoding="utf-8") as handle:
        for action in plan.actions:
            handle.write(f"{action}\n")

    index_cases.append(
        {
            "case_id": case_id,
            "plan_file": plan_rel,
            "step_count": len(plan.actions),
            "validated": True,
        }
    )

with open(index_path, "w", encoding="utf-8") as handle:
    json.dump(
        {
            "shared_domain": manifest["shared_domain"],
            "cases": index_cases,
        },
        handle,
        indent=2,
    )
    handle.write("\n")
PY
