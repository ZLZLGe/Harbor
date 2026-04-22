import json
import os
import subprocess
import sys
from pathlib import Path


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
PACKAGE_PATH = Path(os.environ.get("SUBMISSION_OUTPUT_PATH", "/app/output/submission_package.json"))


def _run_build() -> tuple[subprocess.CompletedProcess[str], dict]:
    build_script = WORKSPACE_ROOT / "build_submission.py"
    completed = subprocess.run(
        [sys.executable, str(build_script)],
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    payload = {}
    if PACKAGE_PATH.exists():
        payload = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    return completed, payload


def test_build_submission_succeeds():
    completed, payload = _run_build()
    assert completed.returncode == 0, completed.stderr
    assert payload["validation_passed"] is True


def test_output_file_has_expected_snapshot_and_api_trace():
    _, payload = _run_build()
    assert payload["snapshot_id"] == "systematic-review-t2d-2026-04-15"
    assert payload["api_trace"]["base_url"] == "http://127.0.0.1:8123"
    assert payload["api_trace"]["health"]["status_code"] == 200
    assert payload["api_trace"]["included_studies"]["status_code"] == 200
    assert payload["api_trace"]["references"]["status_code"] == 200
    assert payload["api_trace"]["summary"]["status_code"] == 200
