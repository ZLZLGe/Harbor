#!/usr/bin/env bash
set -euo pipefail

mkdir -p /logs/verifier

if ! curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
  python /opt/knowledge_service.py >/tmp/knowledge_service.log 2>&1 &
  sleep 0.3
fi

if python -m pytest /tests/test_outputs.py -q --tb=short > /logs/verifier/pytest-output.txt 2>&1; then
  echo 1 > /logs/verifier/reward.txt
  cat /logs/verifier/pytest-output.txt
else
  echo 0 > /logs/verifier/reward.txt
  cat /logs/verifier/pytest-output.txt
  exit 1
fi
