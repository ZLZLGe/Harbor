#!/bin/bash

set -euo pipefail

uv init --python 3.12
uv add pytest==8.4.1
uv add pytest-json-ctrf==0.3.5
uv add openpyxl==3.1.5

if uv run pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "/root/data/regatta_team_leaderboard.xlsx" ]; then
  cp /root/data/regatta_team_leaderboard.xlsx /logs/verifier/regatta_team_leaderboard.xlsx
fi
