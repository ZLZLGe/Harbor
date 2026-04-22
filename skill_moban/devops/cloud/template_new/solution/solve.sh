#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"

cp "$SOLUTION_ROOT/fixed/infra/containerapp.template.json" \
  "$WORKSPACE_ROOT/infra/containerapp.template.json"
cp "$SOLUTION_ROOT/fixed/rollout_api/service.py" \
  "$WORKSPACE_ROOT/rollout-api/rollout_api/service.py"
cp "$SOLUTION_ROOT/fixed/rollout_api/summary_projection.py" \
  "$WORKSPACE_ROOT/rollout-api/rollout_api/summary_projection.py"
