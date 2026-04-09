#!/bin/bash

mkdir -p /logs/verifier
VERIFIER_ROOT=/tmp/dashboard-verifier

kill_servers() {
  fuser -k 3000/tcp 2>/dev/null || true
  fuser -k 3001/tcp 2>/dev/null || true
  pkill -f "next start" 2>/dev/null || true
  pkill -f "tsx src/server.ts" 2>/dev/null || true
  sleep 1
}

kill_servers

if ! curl -s http://localhost:3001/health > /dev/null 2>&1; then
  echo "Starting catalog simulator..."
  cd /services/api-simulator && npm start &
  API_PID=$!

  for i in {1..20}; do
    if curl -s http://localhost:3001/health > /dev/null 2>&1; then
      echo "Catalog simulator ready"
      break
    fi
    sleep 1
  done
fi

cd /app
npm run build
npm start &
APP_PID=$!

echo "Waiting for application server..."
for i in {1..40}; do
  if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "Application server ready"
    break
  fi
  sleep 1
done

rm -rf "$VERIFIER_ROOT"
mkdir -p "$VERIFIER_ROOT/python" "$VERIFIER_ROOT/browsers"
tar -xzf /tests/vendor/python-playwright.tar.gz -C "$VERIFIER_ROOT/python"
tar -xzf /tests/vendor/ms-playwright-chromium.tar.gz -C "$VERIFIER_ROOT/browsers"
export PYTHONPATH="$VERIFIER_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
export PLAYWRIGHT_BROWSERS_PATH="$VERIFIER_ROOT/browsers"

set -o pipefail
python3 /tests/verify_dashboard.py 2>&1 | tee /logs/verifier/pytest-output.txt
PYTEST_EXIT=${PIPESTATUS[0]}
set +o pipefail

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

kill $APP_PID 2>/dev/null || true
kill $API_PID 2>/dev/null || true
kill_servers

exit 0
