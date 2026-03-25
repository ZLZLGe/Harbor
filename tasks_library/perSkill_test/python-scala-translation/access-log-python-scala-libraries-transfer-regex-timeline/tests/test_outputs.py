from __future__ import annotations

import csv
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

SOLUTION_PATH = Path("/root/AccessLogAnalyzer.scala")
PROJECT_DIR = Path("/root/localtest")
PROJECT_SRC_DIR = PROJECT_DIR / "src" / "main" / "scala"
PROJECT_FILE = PROJECT_SRC_DIR / "AccessLogAnalyzer.scala"
INPUT_PATH = Path("/root/challenge/input/access.log")
FIXED_OUTPUT_PATH = Path("/root/challenge/output/session_summary.csv")
CUSTOM_OUTPUT_PATH = Path("/root/challenge/output/session_summary_gap45.csv")
REFERENCE_OUTPUT_PATH = Path("/tmp/reference_session_summary.csv")
REFERENCE_CUSTOM_OUTPUT_PATH = Path("/tmp/reference_session_summary_gap45.csv")
EXPECTED_COLUMNS = [
    "session_id",
    "client_id",
    "user_id",
    "session_start_utc",
    "session_end_utc",
    "duration_minutes",
    "request_count",
    "status_2xx",
    "status_4xx",
    "status_5xx",
    "total_bytes",
    "paths",
]


def load_reference_module():
    spec = importlib.util.spec_from_file_location("access_log_analyzer_ref", "/root/access_log_analyzer.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expected_csv(output_path: Path, gap_minutes: int) -> tuple[list[str], list[dict[str, str]]]:
    module = load_reference_module()
    module.run(INPUT_PATH, output_path, gap_minutes)
    return load_csv(output_path)


def install_solution() -> None:
    assert SOLUTION_PATH.exists(), "missing /root/AccessLogAnalyzer.scala"
    PROJECT_SRC_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOLUTION_PATH, PROJECT_FILE)


def write_harness(name: str, body: str) -> None:
    PROJECT_SRC_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_SRC_DIR / name).write_text(body, encoding="utf-8")


def run_sbt(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sbt", "-batch", command],
        cwd=PROJECT_DIR,
        text=True,
        capture_output=True,
        check=False,
    )


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    assert path.exists(), f"missing csv output: {path}"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_main_writes_expected_csv():
    install_solution()
    result = run_sbt("runMain AccessLogAnalyzer")
    assert result.returncode == 0, result.stdout + result.stderr

    actual_columns, actual_rows = load_csv(FIXED_OUTPUT_PATH)
    expected_columns, expected_rows = expected_csv(REFERENCE_OUTPUT_PATH, 30)
    assert actual_columns == expected_columns
    assert actual_rows == expected_rows


def test_run_supports_custom_session_gap_and_output_path():
    install_solution()
    write_harness(
        "RunGap45.scala",
        """
import java.nio.file.Paths

object RunGap45 {
  def main(args: Array[String]): Unit = {
    AccessLogAnalyzer.run(
      Paths.get("/root/challenge/input/access.log"),
      Paths.get("/root/challenge/output/session_summary_gap45.csv"),
      45
    )
  }
}
""".strip()
        + "\n",
    )
    result = run_sbt("runMain RunGap45")
    assert result.returncode == 0, result.stdout + result.stderr

    actual_columns, actual_rows = load_csv(CUSTOM_OUTPUT_PATH)
    expected_columns, expected_rows = expected_csv(REFERENCE_CUSTOM_OUTPUT_PATH, 45)
    assert actual_columns == expected_columns
    assert actual_rows == expected_rows
    assert len(actual_rows) < len(expected_csv(REFERENCE_OUTPUT_PATH, 30)[1])


def test_csv_contract_is_observable_and_sorted():
    install_solution()
    result = run_sbt("runMain AccessLogAnalyzer")
    assert result.returncode == 0, result.stdout + result.stderr

    columns, rows = load_csv(FIXED_OUTPUT_PATH)
    assert columns == EXPECTED_COLUMNS
    assert rows, "expected at least one session row"

    ordering = [(row["session_start_utc"], row["session_id"]) for row in rows]
    assert ordering == sorted(ordering)
    assert len({row["session_id"] for row in rows}) == len(rows)

    for row in rows:
        request_count = int(row["request_count"])
        status_total = int(row["status_2xx"]) + int(row["status_4xx"]) + int(row["status_5xx"])
        assert request_count == status_total
        assert int(row["duration_minutes"]) >= 0
        assert int(row["total_bytes"]) >= 0
