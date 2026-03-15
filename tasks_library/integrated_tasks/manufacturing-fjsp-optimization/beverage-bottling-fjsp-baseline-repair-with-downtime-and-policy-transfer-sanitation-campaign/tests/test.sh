#!/bin/bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/logs/verifier}"
if ! mkdir -p "${LOG_DIR}" 2>/dev/null; then
  LOG_DIR="$(mktemp -d)"
fi

TEST_FILE="${TEST_FILE:-/tests/test_outputs.py}"
if [ ! -f "${TEST_FILE}" ]; then
  TEST_FILE="$(cd "$(dirname "$0")" && pwd)/test_outputs.py"
fi

if TEST_FILE="${TEST_FILE}" python3 - <<'PY'
import importlib.util
import os
import pathlib

path = pathlib.Path(os.environ["TEST_FILE"])
spec = importlib.util.spec_from_file_location("test_outputs", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

for name in sorted(dir(module)):
    if name.startswith("test_"):
        getattr(module, name)()
PY
then
  echo 1 > "${LOG_DIR}/reward.txt"
else
  echo 0 > "${LOG_DIR}/reward.txt"
  exit 1
fi
