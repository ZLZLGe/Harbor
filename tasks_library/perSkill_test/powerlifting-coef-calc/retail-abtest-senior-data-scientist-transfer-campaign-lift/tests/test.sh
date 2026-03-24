#!/bin/bash

set -euo pipefail

uv init --python 3.12
uv add pytest==8.4.1 pytest-json-ctrf==0.3.5 pandas==2.2.3 openpyxl==3.1.5 numpy==2.1.1

set +e
uv run pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
test_exit=$?
set -e

if [ ${test_exit} -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "/root/data/campaign_lift_analysis.xlsx" ]; then
  cp /root/data/campaign_lift_analysis.xlsx /logs/verifier/campaign_lift_analysis.xlsx
fi
