#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${LOG_DIR:-/logs/verifier}"

if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
    LOG_DIR="/tmp/verifier"
    mkdir -p "$LOG_DIR"
fi

if python3 "$SCRIPT_DIR/test_outputs.py"; then
    echo 1 > "$LOG_DIR/reward.txt"
else
    echo 0 > "$LOG_DIR/reward.txt"
    exit 1
fi
