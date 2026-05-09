#!/usr/bin/env bash

set -euo pipefail

export TASK_ROOT="/app/workspace"
export DB_NAME="movielens_task"
export PGDATA_DIR="/tmp/database-tools-pgdata"
export PGSOCKET_DIR="/tmp/database-tools-pg"
export PGPORT="55432"
export PGUSER="postgres"
export PGHOST="$PGSOCKET_DIR"
export PSQL_BASE=(psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER")
export DATA_DIR="${MOVIELENS_DATA_DIR:-$TASK_ROOT/data}"
