#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path


def quote_for_shell(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def truthy(value: str) -> bool:
    return value.strip().lower() == "true"


def nonempty(value: str) -> str:
    return value.strip()


def build_unit_row(row: dict[str, str]) -> dict[str, str]:
    platform = nonempty(row.get("platform", "")).lower()
    file_filter = nonempty(row.get("file_filter", ""))
    glob_filter = nonempty(row.get("glob_filter", ""))
    grep_filter = nonempty(row.get("grep_filter", ""))
    suite_filter = nonempty(row.get("suite_filter", ""))
    coverage = truthy(row.get("coverage", ""))

    script = ".\\scripts\\test.bat" if platform == "windows" else "./scripts/test.sh"
    arguments: list[str] = []

    if file_filter:
        arguments.append(file_filter)
    elif glob_filter:
        arguments.extend(["--runGlob", quote_for_shell(glob_filter)])

    if grep_filter:
        arguments.extend(["--grep", quote_for_shell(grep_filter)])

    if coverage:
        arguments.append("--coverage")

    if suite_filter:
        notes = "Suite filter is ignored for unit tests; the unit source file path remains the selector."
    elif coverage:
        notes = "Unit request uses scripts/test.sh semantics with the source file path and coverage enabled."
        if not file_filter:
            notes = "Unit request keeps unit-test semantics and enables coverage for the selected filters."
    elif glob_filter:
        notes = "Unit request uses a compiled-test glob and grep filter." if grep_filter else "Unit request uses a compiled-test glob selector."
    elif grep_filter:
        notes = "Unit request uses a grep filter within the unit-test runner."
    else:
        notes = "Unit request uses the default unit-test runner selector."

    return {
        "request_id": nonempty(row.get("request_id", "")),
        "script": script,
        "arguments": " ".join(arguments),
        "scope": "unit",
        "compile_required": "true",
        "notes": notes,
    }


def build_integration_row(row: dict[str, str]) -> dict[str, str]:
    platform = nonempty(row.get("platform", "")).lower()
    file_filter = nonempty(row.get("file_filter", ""))
    glob_filter = nonempty(row.get("glob_filter", ""))
    grep_filter = nonempty(row.get("grep_filter", ""))
    suite_filter = nonempty(row.get("suite_filter", ""))
    coverage = truthy(row.get("coverage", ""))

    script = ".\\scripts\\test-integration.bat" if platform == "windows" else "./scripts/test-integration.sh"
    arguments: list[str] = []

    if suite_filter:
        arguments.extend(["--suite", quote_for_shell(suite_filter)])
        if grep_filter:
            arguments.extend(["--grep", quote_for_shell(grep_filter)])
        scope = "integration-extension"
        notes_parts = ["Suite selection targets extension host tests only"]
        if coverage:
            notes_parts.append("integration coverage is ignored")
        if file_filter or glob_filter:
            notes_parts.append("file and glob filters are ignored")
        notes = "; ".join(notes_parts) + "."
    elif file_filter:
        arguments.extend(["--run", file_filter])
        if grep_filter:
            arguments.extend(["--grep", quote_for_shell(grep_filter)])
        scope = "integration-node"
        notes = "Run targets node integration tests only; extension host suites are skipped by --run."
        if coverage:
            notes = "Run targets node integration tests only; extension host suites are skipped by --run, and integration coverage is ignored."
    elif glob_filter:
        arguments.extend(["--runGlob", quote_for_shell(glob_filter)])
        if grep_filter:
            arguments.extend(["--grep", quote_for_shell(grep_filter)])
        scope = "integration-node"
        notes = "Run glob narrows execution to node integration test files only."
        if coverage:
            notes = "Run glob narrows execution to node integration test files only; integration coverage is ignored."
    else:
        if grep_filter:
            arguments.extend(["--grep", quote_for_shell(grep_filter)])
        scope = "integration-all"
        notes = "Grep-only integration requests run both node integration tests and extension host suites."
        if coverage:
            notes = "Grep-only integration requests run both node integration tests and extension host suites; integration coverage is ignored."

    return {
        "request_id": nonempty(row.get("request_id", "")),
        "script": script,
        "arguments": " ".join(arguments),
        "scope": scope,
        "compile_required": "true",
        "notes": notes,
    }


workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "test_requests.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "vscode_test_selection.csv"
output_dir.mkdir(parents=True, exist_ok=True)

rows: list[dict[str, str]] = []
with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        test_kind = nonempty(row.get("test_kind", "")).lower()
        if test_kind == "integration":
            rows.append(build_integration_row(row))
        else:
            rows.append(build_unit_row(row))

rows.sort(key=lambda item: item["request_id"])

fieldnames = [
    "request_id",
    "script",
    "arguments",
    "scope",
    "compile_required",
    "notes",
]

with output_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
