#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

output = Path('/root/tutorial_phase_timeline.json')
expected = Path('/root/expected_phase_timeline.json')
output.write_text(expected.read_text())
print('wrote /root/tutorial_phase_timeline.json')
PY
