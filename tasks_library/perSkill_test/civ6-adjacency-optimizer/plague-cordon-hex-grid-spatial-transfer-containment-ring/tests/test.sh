#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || \
pip3 install pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || true

LOG_DIR="${LOG_DIR:-/logs/verifier}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"

mkdir -p "$LOG_DIR/scores" "$LOG_DIR/solutions"
cp "$OUTPUT_DIR"/containment_ring.json "$LOG_DIR/solutions/" 2>/dev/null || true

pytest /tests/test_outputs.py -v --tb=short --ctrf "$LOG_DIR/ctrf.json" > "$LOG_DIR/test_output.log" 2>&1

cat "$LOG_DIR/test_output.log"

python3 <<'PY'
import os
from pathlib import Path

log_dir = Path(os.environ.get("LOG_DIR", "/logs/verifier"))
score_file = log_dir / "scores" / "containment_ring.txt"

if score_file.exists():
    try:
        score = float(score_file.read_text().strip())
    except ValueError:
        score = 0.0
else:
    score = 0.0

print(f"containment_ring: {score:.3f}")
with (log_dir / "reward.txt").open("w") as f:
    f.write(f"{score:.3f}")
PY
