import re
import subprocess
from pathlib import Path


def test_primary_outputs_exist() -> None:
    assert Path("/root/similar_fuzz.py").exists()
    assert Path("/root/similar_fuzz.log").exists()
    assert Path("/root/similar_target_notes.md").exists()


def test_driver_contains_target_call() -> None:
    code = Path("/root/similar_fuzz.py").read_text()
    assert "atheris.Fuzz()" in code
    assert "parse_frame" in code


def test_notes_cover_target() -> None:
    notes = Path("/root/similar_target_notes.md").read_text()
    assert "lineproto.parse_frame" in notes
    assert "checksum" in notes


def test_log_has_instrumentation() -> None:
    log = Path("/root/similar_fuzz.log").read_text()
    assert "INFO: Instrumenting" in log
    assert re.search(r"Done\s+\d+\s+in\s+\d+\s+second\(s\)", log)


def test_driver_runs_again() -> None:
    result = subprocess.run(
        ["python", "/root/similar_fuzz.py", "-atheris_runs=5"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "INFO: Instrumenting" in result.stderr
