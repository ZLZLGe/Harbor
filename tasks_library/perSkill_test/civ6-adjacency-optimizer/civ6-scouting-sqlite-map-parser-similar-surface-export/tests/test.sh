#!/bin/bash
set -euo pipefail

if command -v pip3 >/dev/null 2>&1; then
  pip3 install --break-system-packages pytest==8.3.4 2>/dev/null || \
  pip3 install pytest==8.3.4 2>/dev/null || true
fi

mkdir -p /logs/verifier

if python3 - <<'PY' >/dev/null 2>&1
import pytest
PY
then
  set +e
  python3 -m pytest /tests/test_outputs.py -v --tb=short > /logs/verifier/test_output.log 2>&1
  PYTEST_EXIT_CODE=$?
  set -e
else
  set +e
  python3 <<'PY' > /logs/verifier/test_output.log 2>&1
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

pytest_stub = types.ModuleType("pytest")

def fixture(*args, **kwargs):
    def decorator(fn):
        return fn
    return decorator

pytest_stub.fixture = fixture
sys.modules["pytest"] = pytest_stub

spec = importlib.util.spec_from_file_location("task_test_outputs", "/tests/test_outputs.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

output_file = Path(os.environ.get("TASK_OUTPUT_FILE", "/output/civ6_district_surface.json"))
assert output_file.exists(), f"Output file not found: {output_file}"

actual = json.loads(output_file.read_text())
expected = module.build_expected_output()

assert isinstance(actual, dict)
assert set(actual.keys()) == {"map", "request", "plots", "city_center_surface"}
assert actual == expected
print("manual verifier: pass")
PY
  PYTEST_EXIT_CODE=$?
  set -e
fi

cat /logs/verifier/test_output.log

if [ "$PYTEST_EXIT_CODE" -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi

exit 0
