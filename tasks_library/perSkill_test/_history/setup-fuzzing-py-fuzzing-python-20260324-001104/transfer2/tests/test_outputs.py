import re
import subprocess
from pathlib import Path


def test_report_mentions_hooks() -> None:
    report = Path("/root/transfer2_hook_report.txt").read_text()
    assert "RegEx" in report
    assert "str" in report
    assert "rulematcher.evaluate_rule_line" in report


def test_driver_enables_hooks() -> None:
    code = Path("/root/transfer2_fuzz.py").read_text()
    assert 'atheris.enabled_hooks.add("RegEx")' in code
    assert 'atheris.enabled_hooks.add("str")' in code


def test_log_records_run() -> None:
    log = Path("/root/transfer2_regex_fuzz.log").read_text()
    assert "INFO: Instrumenting" in log
    assert re.search(r"Done\s+\d+\s+in\s+\d+\s+second\(s\)", log)


def test_driver_runs_again() -> None:
    result = subprocess.run(
        ["python", "/root/transfer2_fuzz.py", "-atheris_runs=5"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
