#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
WORKSPACE_ROOT=${WORKSPACE_ROOT:-"$ROOT_DIR/workspace"}
export WORKSPACE_ROOT

mkdir -p "$WORKSPACE_ROOT/output"
bash "$ROOT_DIR/solution/solve.sh"
python3 "$ROOT_DIR/tests/test_outputs.py"
