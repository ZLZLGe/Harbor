#!/bin/bash
set -euo pipefail

TEMPLATE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$TEMPLATE_ROOT/workspace}"

bash "$TEMPLATE_ROOT/solution/solve.sh"
WORKSPACE_ROOT="$WORKSPACE_ROOT" python3 "$TEMPLATE_ROOT/tests/test_outputs.py"
