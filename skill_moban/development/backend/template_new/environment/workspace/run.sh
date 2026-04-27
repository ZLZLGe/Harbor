#!/bin/bash
set -euo pipefail

cd /app/workspace
mkdir -p /tmp/shipping-api

cleanup_stale() {
  pkill -f "/app/workspace/services/rate_service.py" >/dev/null 2>&1 || true
  pkill -f "/app/workspace/services/booking_service.py" >/dev/null 2>&1 || true
  pkill -f "/app/workspace/gateway/app.py" >/dev/null 2>&1 || true
}

wait_http() {
  local url="$1"
  for _ in $(seq 1 80); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

cleanup_stale

python3 /app/workspace/services/rate_service.py >/tmp/shipping-api/rate-service.log 2>&1 &
python3 /app/workspace/services/booking_service.py >/tmp/shipping-api/booking-service.log 2>&1 &

wait_http "http://127.0.0.1:9101/health" || {
  cat /tmp/shipping-api/rate-service.log >&2 || true
  exit 1
}
wait_http "http://127.0.0.1:9102/health" || {
  cat /tmp/shipping-api/booking-service.log >&2 || true
  exit 1
}

exec python3 /app/workspace/gateway/app.py
