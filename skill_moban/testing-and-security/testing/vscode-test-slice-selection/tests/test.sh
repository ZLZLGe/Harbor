#!/bin/bash
set +e

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
export TESTS_DIR

python3 - <<'PY'
import importlib.util
import pathlib
import os

candidate_paths = [
    pathlib.Path('/tests/test_outputs.py'),
    pathlib.Path('tests/test_outputs.py'),
    pathlib.Path(os.environ.get('TESTS_DIR', '')) / 'test_outputs.py',
]

test_path = None
for path in candidate_paths:
    if str(path) and path.exists():
        test_path = path
        break

if test_path is None:
    raise FileNotFoundError('Cannot find test_outputs.py in /tests or tests/')

spec = importlib.util.spec_from_file_location('task_test_outputs', test_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
module.test_outputs()
PY
status=$?

if [ -d /logs/verifier ]; then
  if [ "$status" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
  else
    echo 0 > /logs/verifier/reward.txt
  fi
fi

exit "$status"
