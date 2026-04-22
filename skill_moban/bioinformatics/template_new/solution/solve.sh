#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python /services/panel-annotation/server.py >/tmp/panel-annotation.log 2>&1 &
SERVICE_PID=$!
trap 'kill ${SERVICE_PID} >/dev/null 2>&1 || true' EXIT

python "${SCRIPT_DIR}/solve.py"
