#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}" bash solution/solve.sh
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}" python3 tests/test_outputs.py
