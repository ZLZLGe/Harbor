#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import shutil
from pathlib import Path

config = json.loads(Path('/root/reference/task_config.json').read_text())
reference_root = Path('/root/reference/files')
workspace_root = Path('/workspace')

for operation in config['copy_operations']:
    source = reference_root / operation['source']
    target = workspace_root / operation['target']
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

summary_path = Path(config['summary_file'])
summary_path.parent.mkdir(parents=True, exist_ok=True)
lines = [f"# {config['summary_title']}", ""]
for item in config['summary_points']:
    lines.append(f"- {item}")
summary_path.write_text("\n".join(lines) + "\n")
PY
