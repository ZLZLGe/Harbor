#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED_DIR="$SCRIPT_DIR/fixed"
WORKSPACE_ROOT="/app/workspace"

cp "$FIXED_DIR/common.py" "$WORKSPACE_ROOT/marketplace_snapshot/common.py"
cp "$FIXED_DIR/pipeline.py" "$WORKSPACE_ROOT/marketplace_snapshot/pipeline.py"
cp "$FIXED_DIR/publish.py" "$WORKSPACE_ROOT/marketplace_snapshot/publish.py"

if ! curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then
  nohup python3 /services/audit-service/server.pyc >/tmp/marketplace-audit.log 2>&1 &
  for i in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

make -C "$WORKSPACE_ROOT" clean
PYTHONPATH="$WORKSPACE_ROOT" python3 -m marketplace_snapshot.cli publish
