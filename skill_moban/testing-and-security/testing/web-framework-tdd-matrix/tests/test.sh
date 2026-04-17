#!/bin/bash
set +e

python3 - <<'PY'
import importlib.util
import pathlib

candidate_paths = [
    pathlib.Path('/tests/test_outputs.py'),
    pathlib.Path('tests/test_outputs.py'),
]

for path in candidate_paths:
    if path.exists():
        spec = importlib.util.spec_from_file_location('task_test_outputs', path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        module.test_outputs()
        raise SystemExit(0)

raise FileNotFoundError('Cannot find test_outputs.py in /tests or tests/')
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
