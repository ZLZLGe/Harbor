#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TEMPLATE_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$TEMPLATE_DIR/workspace}"

python3 "$SCRIPT_DIR/generate_plan.py"
