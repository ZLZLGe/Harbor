#!/bin/bash

mkdir -p /logs/verifier

kill_servers() {
  fuser -k 3000/tcp 2>/dev/null || true
  fuser -k 3001/tcp 2>/dev/null || true
  pkill -f "next start" 2>/dev/null || true
  pkill -f "/services/api-simulator/src/server.js" 2>/dev/null || true
  sleep 1
}

kill_servers

if ! curl -s http://localhost:3001/health >/dev/null 2>&1; then
  cd /services/api-simulator && npm start >/logs/verifier/simulator.log 2>&1 &
  API_PID=$!
  for _ in $(seq 1 20); do
    if curl -s http://localhost:3001/health >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

cd /app
npm run build >/logs/verifier/build.log 2>&1
BUILD_EXIT=$?

if [ "$BUILD_EXIT" -ne 0 ]; then
  echo 0 > /logs/verifier/reward.txt
  cat /logs/verifier/build.log
  exit 0
fi

npm start >/logs/verifier/app.log 2>&1 &
APP_PID=$!

for _ in $(seq 1 30); do
  if curl -s http://localhost:3000/control-room >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

set +e
pytest /tests/test_outputs.py -v --tb=short 2>&1 | tee /logs/verifier/pytest-output.txt
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

kill $APP_PID 2>/dev/null || true
kill $API_PID 2>/dev/null || true
kill_servers

exit 0
