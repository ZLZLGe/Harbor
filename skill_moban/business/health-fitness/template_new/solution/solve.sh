#!/bin/bash
set -euo pipefail

mkdir -p /root/output

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/solve.py"
