#!/bin/bash
set -euo pipefail

python3 -m pip install --break-system-packages \
  pytest==8.4.1 \
  pytest-json-ctrf==0.3.5

if pytest --capture=tee-sys --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
