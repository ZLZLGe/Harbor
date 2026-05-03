#!/bin/bash
set -euo pipefail

if command -v start-content-review >/dev/null 2>&1; then
  start-content-review
fi

python3 /solution/solve.py
