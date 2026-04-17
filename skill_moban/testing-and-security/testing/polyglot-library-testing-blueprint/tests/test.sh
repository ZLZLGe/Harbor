#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
WORKSPACE_ROOT=${WORKSPACE_ROOT:-"$ROOT_DIR/workspace"}
export WORKSPACE_ROOT

if [ -f /tests/test_outputs.py ]; then
  python3 /tests/test_outputs.py
else
  python3 "$ROOT_DIR/tests/test_outputs.py"
fi
