#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_FILE="$SCRIPT_DIR/test_outputs.py"

if python3 - <<'PY'
import importlib.util
import sys

sys.exit(0 if importlib.util.find_spec("pytest") else 1)
PY
then
    if [ -d /logs/verifier ]; then
        if python3 -m pytest "$TEST_FILE" --ctrf=/logs/verifier/ctrf.json -v; then
            echo "1" > /logs/verifier/reward.txt
        else
            echo "0" > /logs/verifier/reward.txt
        fi
        exit 0
    fi

    python3 -m pytest "$TEST_FILE" -v
    exit 0
fi

if [ -d /logs/verifier ]; then
    TEST_FILE="$TEST_FILE" python3 - <<'PY'
from pathlib import Path
import importlib.util
import os

path = Path(os.environ["TEST_FILE"])
spec = importlib.util.spec_from_file_location("test_outputs", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

for name in dir(module):
    obj = getattr(module, name)
    if isinstance(obj, type) and name.startswith("Test"):
        instance = obj()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                getattr(instance, method_name)()
PY
    echo "1" > /logs/verifier/reward.txt
    exit 0
fi

TEST_FILE="$TEST_FILE" python3 - <<'PY'
from pathlib import Path
import importlib.util
import os

path = Path(os.environ["TEST_FILE"])
spec = importlib.util.spec_from_file_location("test_outputs", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

for name in dir(module):
    obj = getattr(module, name)
    if isinstance(obj, type) and name.startswith("Test"):
        instance = obj()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                getattr(instance, method_name)()
PY
