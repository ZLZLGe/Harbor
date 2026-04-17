#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TEMPLATE_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$TEMPLATE_DIR/workspace}"

bash "$TEMPLATE_DIR/solution/solve.sh"
python3 "$TEMPLATE_DIR/tests/test_outputs.py"
