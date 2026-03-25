#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -q; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

python3 - <<'PY'
import json
import shutil
from pathlib import Path
config = json.loads(Path('/root/data/task_config.json').read_text())
path = Path(config['output_file'])
if path.exists():
    shutil.copy2(path, Path('/logs/verifier') / path.name)
PY

exit 0
