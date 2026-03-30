#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DB_NAME=${1:-support_dashboard}

export PGHOST=${PGHOST:-/tmp/support-dashboard-pg}
export PGPORT=${PGPORT:-55432}
export PGUSER=${PGUSER:-postgres}

psql -v ON_ERROR_STOP=1 -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -v ON_ERROR_STOP=1 -d postgres -c "CREATE DATABASE $DB_NAME;"
psql -v ON_ERROR_STOP=1 -d "$DB_NAME" -f "$SCRIPT_DIR/../support_seed.sql"
