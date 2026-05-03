#!/bin/bash
set -euo pipefail

VERIFIER_DIR="${VERIFIER_DIR:-/logs/verifier}"
ANSWER_DIR="${TASK_ANSWER_DIR:-/root/answer}"
REGISTRY_LOG_PATH="${SOURCE_REGISTRY_LOG_PATH:-/tmp/source-registry-requests.log}"
REGISTRY_PORT="${SOURCE_REGISTRY_PORT:-4873}"
SOURCE_REGISTRY_SERVER="${SOURCE_REGISTRY_SERVER:-/services/source-registry/server.py}"

mkdir -p "$VERIFIER_DIR" "$ANSWER_DIR"
rm -f "$REGISTRY_LOG_PATH"
rm -f "$ANSWER_DIR/presentation.html" "$ANSWER_DIR/presentation_manifest.json" "$ANSWER_DIR/source_audit.json"

python3 "$SOURCE_REGISTRY_SERVER" >/tmp/source-registry-test.log 2>&1 &
SERVICE_PID=$!
trap 'kill ${SERVICE_PID} >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${REGISTRY_PORT}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

set +e
python3 -m pytest -q /tests/test_outputs.py /tests/test_guardrails.py 2>&1 | tee "$VERIFIER_DIR/pytest-output.txt"
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_DIR/reward.txt"
  printf '{"reward": 1.0}\n' > "$VERIFIER_DIR/result.json"
else
  echo 0 > "$VERIFIER_DIR/reward.txt"
  printf '{"reward": 0.0}\n' > "$VERIFIER_DIR/result.json"
fi

exit 0
