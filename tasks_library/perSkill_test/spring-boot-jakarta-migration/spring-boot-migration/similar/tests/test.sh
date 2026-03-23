#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py > /logs/verifier/test_output.log 2>&1; then
  echo 1 > /logs/verifier/reward.txt
else
  cat /logs/verifier/test_output.log
  echo 0 > /logs/verifier/reward.txt
fi

python3 - <<'PY'
import json
import shutil
from pathlib import Path

config = json.loads(Path('/root/reference/task_config.json').read_text())
summary_path = Path(config['summary_file'])
if summary_path.exists():
    shutil.copy2(summary_path, Path('/logs/verifier') / summary_path.name)
PY

exit 0
