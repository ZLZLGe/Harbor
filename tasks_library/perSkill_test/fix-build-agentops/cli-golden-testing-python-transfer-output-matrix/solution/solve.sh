#!/usr/bin/env bash
set -euo pipefail

cd /workspace/shift-digest
mkdir -p artifacts tests

cat <<'EOF' > artifacts/cli_case_matrix.json
{
  "tool": "shift_digest.cli",
  "cases": [
    {
      "case_id": "weekday-team-min20",
      "kind": "success",
      "input": "sample_data/weekday.csv",
      "args": ["--group-by", "team", "--min-minutes", "20"],
      "expected_exit_code": 0,
      "expected_output_lines": [
        "Shift Digest",
        "group_by=team",
        "rows=3",
        "groups=2",
        "1. api | tickets=2 | total_minutes=55",
        "2. ops | tickets=1 | total_minutes=22"
      ]
    },
    {
      "case_id": "weekend-owner-min30-include-cancelled",
      "kind": "success",
      "input": "sample_data/weekend.csv",
      "args": ["--group-by", "owner", "--min-minutes", "30", "--include-cancelled"],
      "expected_exit_code": 0,
      "expected_output_lines": [
        "Shift Digest",
        "group_by=owner",
        "rows=3",
        "groups=3",
        "1. Eli | tickets=1 | total_minutes=120",
        "2. Ada | tickets=1 | total_minutes=40",
        "3. Dia | tickets=1 | total_minutes=40"
      ]
    },
    {
      "case_id": "weekday-status-min10",
      "kind": "success",
      "input": "sample_data/weekday.csv",
      "args": ["--group-by", "status", "--min-minutes", "10"],
      "expected_exit_code": 0,
      "expected_output_lines": [
        "Shift Digest",
        "group_by=status",
        "rows=4",
        "groups=2",
        "1. closed | tickets=2 | total_minutes=52",
        "2. open | tickets=2 | total_minutes=35"
      ]
    },
    {
      "case_id": "missing-duration-column",
      "kind": "error",
      "input": "sample_data/missing_duration.csv",
      "args": ["--group-by", "team"],
      "expected_exit_code": 1,
      "expected_stderr": "Missing required columns: duration_minutes"
    },
    {
      "case_id": "weekend-no-matches",
      "kind": "error",
      "input": "sample_data/weekend.csv",
      "args": ["--group-by", "team", "--min-minutes", "200"],
      "expected_exit_code": 1,
      "expected_stderr": "No records matched the provided filters."
    }
  ]
}
EOF

cat <<'EOF' > tests/test_cli_golden.py
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "artifacts" / "cli_case_matrix.json"


def load_cases(kind: str) -> list[dict[str, object]]:
    payload = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    return [case for case in payload["cases"] if case["kind"] == kind]


def run_cli(case: dict[str, object], output_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = (
        src_path if not existing_pythonpath else f"{src_path}:{existing_pythonpath}"
    )
    command = [
        sys.executable,
        "-m",
        "shift_digest.cli",
        "--input",
        str(REPO_ROOT / str(case["input"])),
        *[str(item) for item in case["args"]],
        "--output",
        str(output_path),
    ]
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, env=env)


@pytest.mark.parametrize("case", load_cases("success"), ids=lambda case: case["case_id"])
def test_success_cases(case: dict[str, object], tmp_path: Path) -> None:
    output_path = tmp_path / f"{case['case_id']}.txt"
    result = run_cli(case, output_path)

    assert result.returncode == case["expected_exit_code"]
    assert result.stderr == ""
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").splitlines() == case["expected_output_lines"]


@pytest.mark.parametrize("case", load_cases("error"), ids=lambda case: case["case_id"])
def test_error_cases(case: dict[str, object], tmp_path: Path) -> None:
    output_path = tmp_path / f"{case['case_id']}.txt"
    result = run_cli(case, output_path)

    assert result.returncode == case["expected_exit_code"]
    assert not output_path.exists()
    assert str(case["expected_stderr"]) in result.stderr
EOF

pytest -q tests/test_cli_golden.py
