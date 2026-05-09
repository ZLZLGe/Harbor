#!/usr/bin/env bash

set -euo pipefail

export TASK_ROOT="${TASK_ROOT:-/app/workspace}"
export DATA_DIR="${MOVIELENS_DATA_DIR:-$TASK_ROOT/data}"
export OUTPUT_DIR="$TASK_ROOT/output"

export PGDATA="${PGDATA:-/tmp/database-tools-pgdata}"
export PGHOST="${PGHOST:-/tmp/database-tools-pg}"
export PGPORT="${PGPORT:-55432}"
export PGUSER="${PGUSER:-postgres}"
export DB_NAME="${DB_NAME:-movielens_task}"
export PGLOG="${PGLOG:-/tmp/database-tools-postgres.log}"

psql_db() {
    psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" "$@"
}

psql_maintenance() {
    psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres "$@"
}

db_exists() {
    psql_maintenance -Atqc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q '^1$'
}
