#!/bin/bash
set -euo pipefail

cp /solution/fixed_run_transient_triage.py /root/environment/pipeline/run_transient_triage.py
chmod +x /root/environment/pipeline/run_transient_triage.py

python /services/field-context/server.py >/tmp/field-context-solve.log 2>&1 &
SERVICE_PID=$!
trap 'kill ${SERVICE_PID} >/dev/null 2>&1 || true' EXIT
sleep 1

python /root/environment/pipeline/run_transient_triage.py --output /root/answer
