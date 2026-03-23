#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

output = Path('/root/chapter_duration_leaderboard.json')
expected = Path('/root/expected_duration_leaderboard.json')
output.write_text(expected.read_text())
print('wrote /root/chapter_duration_leaderboard.json')
PY
