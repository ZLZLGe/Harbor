import json
import re
import subprocess
from pathlib import Path


def test_summary_exists() -> None:
    summary = json.loads(Path("/root/transfer1_summary.json").read_text())
    assert summary["target_function"] == "zipmanifest.load_manifest"
    assert summary["uses_custom_mutator"] is True


def test_driver_mentions_custom_mutator() -> None:
    code = Path("/root/transfer1_fuzz.py").read_text()
    assert "custom_mutator=CustomMutator" in code
    assert "zlib.decompress" in code


def test_log_records_run() -> None:
    log = Path("/root/transfer1_custom_mutator.log").read_text()
    assert "INFO: Instrumenting" in log
    assert re.search(r"Done\s+\d+\s+in\s+\d+\s+second\(s\)", log)


def test_driver_runs_again() -> None:
    result = subprocess.run(
        ["python", "/root/transfer1_fuzz.py", "-atheris_runs=5"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
