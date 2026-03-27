import re
import subprocess
from pathlib import Path


def test_report_mentions_strategy() -> None:
    report = Path("/root/transfer3_instrumentation_report.md").read_text()
    assert "atheris.instrument_all()" in report
    assert "dispatchdsl.load_config" in report


def test_driver_uses_global_instrumentation() -> None:
    code = Path("/root/transfer3_fuzz.py").read_text()
    assert "atheris.instrument_all()" in code
    assert "@atheris.instrument_func" in code


def test_log_records_run() -> None:
    log = Path("/root/transfer3_dispatch.log").read_text()
    assert "INFO: Instrumenting" in log
    assert re.search(r"Done\s+\d+\s+in\s+\d+\s+second\(s\)", log)


def test_driver_runs_again() -> None:
    result = subprocess.run(
        ["python", "/root/transfer3_fuzz.py", "-atheris_runs=5"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
