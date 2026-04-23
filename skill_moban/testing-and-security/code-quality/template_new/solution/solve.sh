#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED_DIR="$SCRIPT_DIR/fixed"
WORKSPACE_ROOT="/app/workspace"

mkdir -p "$WORKSPACE_ROOT/quality"

cp "$FIXED_DIR/exporter.py" "$WORKSPACE_ROOT/settlement_quality/exporter.py"
cp "$FIXED_DIR/gateway_client.py" "$WORKSPACE_ROOT/settlement_quality/gateway_client.py"
cp "$FIXED_DIR/gate.py" "$WORKSPACE_ROOT/settlement_quality/gate.py"
cp "$FIXED_DIR/run_quality_gate.py" "$WORKSPACE_ROOT/scripts/run_quality_gate.py"
cp "$FIXED_DIR/AGENTS.md" "$WORKSPACE_ROOT/AGENTS.md"
cp "$FIXED_DIR/QUALITY.md" "$WORKSPACE_ROOT/quality/QUALITY.md"
cp "$FIXED_DIR/RUN_CODE_REVIEW.md" "$WORKSPACE_ROOT/quality/RUN_CODE_REVIEW.md"
cp "$FIXED_DIR/RUN_INTEGRATION_TESTS.md" "$WORKSPACE_ROOT/quality/RUN_INTEGRATION_TESTS.md"
cp "$FIXED_DIR/RUN_SPEC_AUDIT.md" "$WORKSPACE_ROOT/quality/RUN_SPEC_AUDIT.md"
cp "$FIXED_DIR/test_functional.py" "$WORKSPACE_ROOT/quality/test_functional.py"

make -C "$WORKSPACE_ROOT" clean
make -C "$WORKSPACE_ROOT" quality-gate
