#!/bin/bash
set -euo pipefail

APP_HOME=${APP_HOME:-/root/report-service}
APP_PORT=${APP_PORT:-18080}
JAR_PATH="${APP_HOME}/target/report-preview-0.0.1-SNAPSHOT.jar"

if [ ! -f "${JAR_PATH}" ]; then
  echo "Missing built application jar at ${JAR_PATH}" >&2
  exit 1
fi

nohup java -jar "${JAR_PATH}" --server.port="${APP_PORT}" > /tmp/report-preview.log 2>&1 &

READY=0
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${APP_PORT}/api/reports/health" > /dev/null; then
    READY=1
    break
  fi
  sleep 2
done

if [ "${READY}" -ne 1 ]; then
  tail -n 200 /tmp/report-preview.log || true
  exit 1
fi

python3 -m venv /tmp/report-preview-venv
source /tmp/report-preview-venv/bin/activate
pip install -q pytest requests

set +e
pytest /tests/test_outputs.py -rA -v
STATUS=$?
set -e

mkdir -p /logs/verifier
if [ "${STATUS}" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "${STATUS}"
