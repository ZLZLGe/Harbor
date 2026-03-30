#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DB_NAME=${1:-worker_queue}

export PGHOST=${PGHOST:-/tmp/worker-queue-pg}
export PGPORT=${PGPORT:-55433}
export PGUSER=${PGUSER:-postgres}

psql -v ON_ERROR_STOP=1 -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -v ON_ERROR_STOP=1 -d postgres -c "DROP ROLE IF EXISTS queue_worker;"
psql -v ON_ERROR_STOP=1 -d postgres -c "CREATE ROLE queue_worker LOGIN;"
psql -v ON_ERROR_STOP=1 -d postgres -c "CREATE DATABASE $DB_NAME;"
psql -v ON_ERROR_STOP=1 -d "$DB_NAME" -f "$SCRIPT_DIR/../worker_queue_seed.sql"
