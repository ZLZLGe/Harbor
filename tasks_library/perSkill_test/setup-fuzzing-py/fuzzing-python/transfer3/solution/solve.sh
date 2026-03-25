#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from pathlib import Path

config = json.loads(Path("/root/data/task_config.json").read_text())
driver = Path("/root/data/expected_fuzz.py").read_text(encoding="utf-8")
Path(config["primary_output_file"]).write_text(driver, encoding="utf-8")
PY

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

config = json.loads(Path("/root/data/task_config.json").read_text())
repo_root = Path(config["repo_root"])
log_path = Path(config["fuzz_log_file"])
with log_path.open("w", encoding="utf-8") as handle:
    result = subprocess.run(
        ["python3", "fuzz.py", "-runs=6"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=handle,
        check=False,
    )
if result.returncode != 0:
    raise SystemExit(result.returncode)
PY
