import ast
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path("/workspace/shift-digest")
TEST_FILE = REPO_ROOT / "tests" / "test_cli_golden.py"
MATRIX_PATH = REPO_ROOT / "artifacts" / "cli_case_matrix.json"

EXPECTED_CASES = {
    "weekday-team-min20": {
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
            "2. ops | tickets=1 | total_minutes=22",
        ],
    },
    "weekend-owner-min30-include-cancelled": {
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
            "3. Dia | tickets=1 | total_minutes=40",
        ],
    },
    "weekday-status-min10": {
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
            "2. open | tickets=2 | total_minutes=35",
        ],
    },
    "missing-duration-column": {
        "kind": "error",
        "input": "sample_data/missing_duration.csv",
        "args": ["--group-by", "team"],
        "expected_exit_code": 1,
        "expected_stderr": "Missing required columns: duration_minutes",
    },
    "weekend-no-matches": {
        "kind": "error",
        "input": "sample_data/weekend.csv",
        "args": ["--group-by", "team", "--min-minutes", "200"],
        "expected_exit_code": 1,
        "expected_stderr": "No records matched the provided filters.",
    },
}


def make_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else f"{src_path}:{existing}"
    return env


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=make_env(),
    )


def is_parametrize_decorator(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "parametrize"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "mark"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "pytest"
    )


def test_matrix_file_matches_required_contract():
    assert MATRIX_PATH.exists(), "缺少 artifacts/cli_case_matrix.json"

    payload = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    assert payload.get("tool") == "shift_digest.cli"
    assert isinstance(payload.get("cases"), list)
    assert len(payload["cases"]) == 5

    actual_by_id = {case["case_id"]: case for case in payload["cases"]}
    assert set(actual_by_id) == set(EXPECTED_CASES)

    for case_id, expected in EXPECTED_CASES.items():
        actual = actual_by_id[case_id]
        assert actual["kind"] == expected["kind"]
        assert actual["input"] == expected["input"]
        assert actual["args"] == expected["args"]
        assert actual["expected_exit_code"] == expected["expected_exit_code"]
        if expected["kind"] == "success":
            assert actual["expected_output_lines"] == expected["expected_output_lines"]
        else:
            assert actual["expected_stderr"] == expected["expected_stderr"]


def test_matrix_expectations_match_real_cli_behavior(tmp_path: Path):
    payload = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    for case in payload["cases"]:
        output_path = tmp_path / f"{case['case_id']}.txt"
        result = run_command(
            sys.executable,
            "-m",
            "shift_digest.cli",
            "--input",
            str(REPO_ROOT / case["input"]),
            *case["args"],
            "--output",
            str(output_path),
        )

        assert result.returncode == case["expected_exit_code"], case["case_id"]
        if case["kind"] == "success":
            assert output_path.exists(), case["case_id"]
            assert (
                output_path.read_text(encoding="utf-8").splitlines()
                == case["expected_output_lines"]
            ), case["case_id"]
        else:
            assert not output_path.exists(), case["case_id"]
            assert case["expected_stderr"] in result.stderr, case["case_id"]


def test_authored_test_file_has_required_structure():
    assert TEST_FILE.exists(), "缺少 tests/test_cli_golden.py"

    source = TEST_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    parametrize_count = 0
    has_tmp_path = False
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if any(is_parametrize_decorator(decorator) for decorator in node.decorator_list):
            parametrize_count += 1
        if any(arg.arg == "tmp_path" for arg in node.args.args):
            has_tmp_path = True

    assert parametrize_count >= 2, "至少需要两个 pytest 参数化测试"
    assert has_tmp_path, "成功案例应使用 tmp_path 生成输出路径"


def test_authored_test_file_collects_at_least_five_cases():
    result = run_command(sys.executable, "-m", "pytest", "--collect-only", "-q", str(TEST_FILE))
    assert result.returncode == 0, result.stdout + result.stderr

    collected = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("tests/test_cli_golden.py::")
    ]
    assert len(collected) >= 5, result.stdout


def test_authored_tests_pass():
    result = run_command(sys.executable, "-m", "pytest", "-q", str(TEST_FILE))
    assert result.returncode == 0, result.stdout + result.stderr
