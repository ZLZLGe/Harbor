#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"

cp "$SOLUTION_ROOT/fixed/checkout_api/service.py" \
  "$WORKSPACE_ROOT/checkout-api/checkout_api/service.py"
cp "$SOLUTION_ROOT/fixed/checkout_api/main.py" \
  "$WORKSPACE_ROOT/checkout-api/checkout_api/main.py"
