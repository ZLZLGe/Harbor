#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "${SCRIPT_DIR}/fixed_run_analysis.py" /root/environment/pipeline/run_analysis.py
chmod +x /root/environment/pipeline/run_analysis.py

python /services/promo-enrichment/server.py >/tmp/promo-enrichment-solution.log 2>&1 &
SERVICE_PID=$!
trap 'kill "${SERVICE_PID}" >/dev/null 2>&1 || true' EXIT
sleep 0.5

python /root/environment/pipeline/run_analysis.py --output /root/answer
