#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if python3 "$SCRIPT_DIR/test_outputs.py"; then
  if [ -d /logs/verifier ]; then
    echo 1 > /logs/verifier/reward.txt
  fi
else
  if [ -d /logs/verifier ]; then
    echo 0 > /logs/verifier/reward.txt
  fi
  exit 1
fi
