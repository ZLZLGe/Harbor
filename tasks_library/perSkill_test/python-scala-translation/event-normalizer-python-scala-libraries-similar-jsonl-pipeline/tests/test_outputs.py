from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

SOLUTION_PATH = Path("/root/EventNormalizer.scala")
PROJECT_DIR = Path("/root/localtest")
PROJECT_SRC_DIR = PROJECT_DIR / "src" / "main" / "scala"
PROJECT_FILE = PROJECT_SRC_DIR / "EventNormalizer.scala"
INPUT_PATH = Path("/root/challenge/input/events.jsonl")
FIXED_OUTPUT_PATH = Path("/root/challenge/output/daily_report.json")
CUSTOM_OUTPUT_PATH = Path("/root/challenge/output/custom_report.json")
REFERENCE_OUTPUT_PATH = Path("/tmp/reference_daily_report.json")


def load_reference_module():
    spec = importlib.util.spec_from_file_location("event_normalizer_ref", "/root/event_normalizer.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expected_report() -> dict:
    module = load_reference_module()
    module.run(INPUT_PATH, REFERENCE_OUTPUT_PATH)
    return json.loads(REFERENCE_OUTPUT_PATH.read_text(encoding="utf-8"))


def install_solution() -> None:
    assert SOLUTION_PATH.exists(), "missing /root/EventNormalizer.scala"
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


def load_output(path: Path) -> dict:
    assert path.exists(), f"missing report: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_main_writes_fixed_report():
    install_solution()
    result = run_sbt("runMain EventNormalizer")
    assert result.returncode == 0, result.stdout + result.stderr
    assert load_output(FIXED_OUTPUT_PATH) == expected_report()


def test_run_method_supports_custom_output_path():
    install_solution()
    write_harness(
        "RunCustom.scala",
        """
import java.nio.file.Paths

object RunCustom {
  def main(args: Array[String]): Unit = {
    EventNormalizer.run(
      Paths.get("/root/challenge/input/events.jsonl"),
      Paths.get("/root/challenge/output/custom_report.json")
    )
  }
}
""".strip()
        + "\n",
    )
    result = run_sbt("runMain RunCustom")
    assert result.returncode == 0, result.stdout + result.stderr
    assert load_output(CUSTOM_OUTPUT_PATH) == expected_report()
