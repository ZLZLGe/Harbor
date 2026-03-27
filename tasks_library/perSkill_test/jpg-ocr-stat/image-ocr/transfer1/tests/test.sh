#!/bin/bash
set +e

python3 - <<'PY'
import importlib.util
import pathlib
import sys

test_path = pathlib.Path('/tests/test_outputs.py')
spec = importlib.util.spec_from_file_location('task_test_outputs', test_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
module.test_outputs()
PY
status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
