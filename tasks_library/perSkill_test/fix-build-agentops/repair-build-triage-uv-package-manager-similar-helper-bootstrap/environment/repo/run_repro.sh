#!/bin/bash
set -euo pipefail

REPO_ROOT=/opt/build-triage-helper/workspace/failed_copy

cd "$REPO_ROOT"
python3 -m compileall triage_app >/tmp/triage-compile.log
python3 -m triage_app input/build_requests.json output/triage_summary.txt

python3 - <<'PY'
import json
import tomllib
from pathlib import Path

from triage_app import build_triage_summary

root = Path("/opt/build-triage-helper/workspace/failed_copy")
records = json.loads((root / "input" / "build_requests.json").read_text(encoding="utf-8"))["services"]
expected = (root / "expected" / "triage_summary.txt").read_text(encoding="utf-8")
actual = build_triage_summary(records)
pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
script_target = pyproject["project"]["scripts"]["triage-helper"]
if script_target != "triage_app.engine:main":
    raise SystemExit("triage-helper entry point is still incorrect")
if actual != expected:
    raise SystemExit("build_triage_summary() returned the wrong content")
PY

diff -u expected/triage_summary.txt output/triage_summary.txt
