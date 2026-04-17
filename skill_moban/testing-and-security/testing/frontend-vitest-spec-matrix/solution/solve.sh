#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
export WORKSPACE_ROOT

python3 <<'PY'
import csv
import os
from pathlib import Path


INPUT_HEADERS = [
    "target_id",
    "target_type",
    "has_async",
    "has_query_state",
    "has_http_mock",
    "has_error_state",
    "complexity",
]

OUTPUT_HEADERS = [
    "target_id",
    "test_style",
    "required_scenarios",
    "mock_strategy",
    "rtl_tools",
    "coverage_goal",
    "execution_order",
]

TYPE_PRIORITY = {
    "utility": 0,
    "hook": 1,
    "component": 2,
}


def as_bool(raw: str) -> bool:
    return raw.strip().lower() == "yes"


def base_scenarios(target_type: str) -> list[str]:
    if target_type == "component":
        return ["render-baseline", "semantic-selectors"]
    if target_type == "hook":
        return ["invoke-baseline", "observable-state-assertions"]
    return ["input-output-contract", "observable-state-assertions"]


def test_style(target_type: str) -> str:
    if target_type == "component":
        return "vitest rtl component black-box"
    if target_type == "hook":
        return "vitest rtl hook black-box"
    return "vitest unit black-box"


def mock_strategy(query_state: bool, http_mock: bool) -> str:
    if query_state and http_mock:
        return "mock network boundary only; use real nuqs adapter"
    if query_state:
        return "use real nuqs adapter; mock external boundary only"
    return "prefer real collaborators; mock external boundary only"


def rtl_tools(target_type: str, has_async: bool, query_state: bool, http_mock: bool) -> str:
    if target_type == "component":
        tools = ["render", "screen", "userEvent"]
    elif target_type == "hook":
        tools = ["renderHook", "act"]
    else:
        tools = ["vi.fn"]

    if has_async:
        tools.append("waitFor")
    if query_state:
        tools.append("NuqsTestingAdapter")
    if http_mock:
        tools.append("nock")
    return ";".join(tools)


def coverage_goal(complexity: int) -> str:
    if complexity <= 2:
        return "baseline behavior coverage"
    if complexity <= 4:
        return "branch coverage for common states"
    return "state matrix coverage including edge cases"


workspace_root = Path(os.environ["WORKSPACE_ROOT"])
input_path = workspace_root / "frontend_targets.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "frontend_test_matrix.csv"

with input_path.open("r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    if reader.fieldnames != INPUT_HEADERS:
        raise SystemExit(f"Unexpected input headers: {reader.fieldnames}")
    source_rows = list(reader)

execution_rank = sorted(
    source_rows,
    key=lambda row: (
        TYPE_PRIORITY[row["target_type"]],
        int(row["complexity"]),
        row["target_id"],
    ),
)
execution_order_map = {
    row["target_id"]: f"{index:02d}"
    for index, row in enumerate(execution_rank, start=1)
}

output_rows = []
for row in sorted(source_rows, key=lambda item: item["target_id"]):
    target_type = row["target_type"]
    has_async = as_bool(row["has_async"])
    query_state = as_bool(row["has_query_state"])
    http_mock = as_bool(row["has_http_mock"])
    error_state = as_bool(row["has_error_state"])
    complexity = int(row["complexity"])

    scenarios = base_scenarios(target_type)
    if has_async:
        scenarios.append("async-state-settling")
    if query_state:
        scenarios.append("url-query-sync")
    if http_mock:
        scenarios.append("http-success-and-empty")
    if error_state:
        scenarios.append("error-boundary-or-fallback")

    output_rows.append(
        {
            "target_id": row["target_id"],
            "test_style": test_style(target_type),
            "required_scenarios": ";".join(scenarios),
            "mock_strategy": mock_strategy(query_state, http_mock),
            "rtl_tools": rtl_tools(target_type, has_async, query_state, http_mock),
            "coverage_goal": coverage_goal(complexity),
            "execution_order": execution_order_map[row["target_id"]],
        }
    )

output_dir.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS)
    writer.writeheader()
    writer.writerows(output_rows)
PY
