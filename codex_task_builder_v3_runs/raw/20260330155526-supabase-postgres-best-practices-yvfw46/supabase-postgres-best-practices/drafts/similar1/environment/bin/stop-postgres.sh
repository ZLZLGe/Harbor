#!/bin/bash

set -euo pipefail

DATA_DIR=/tmp/support-dashboard-pgdata

if [ -s "$DATA_DIR/postmaster.pid" ]; then
  su postgres -c "pg_ctl -D '$DATA_DIR' -m fast stop" >/dev/null
fi
