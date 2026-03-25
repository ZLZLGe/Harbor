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

config_path = Path("/root/data/task_config.json")
if config_path.exists():
    config = json.loads(config_path.read_text())
    output_file = Path(config["output_file"])
    if output_file.exists():
        shutil.copy2(output_file, Path("/logs/verifier") / output_file.name)
PY

exit 0
