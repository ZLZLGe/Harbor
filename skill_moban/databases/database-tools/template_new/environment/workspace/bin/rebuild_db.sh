#!/usr/bin/env bash

set -euo pipefail

source /app/workspace/bin/common.sh
/app/workspace/bin/start_postgres.sh >/dev/null

dropdb --if-exists -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$DB_NAME"
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$DB_NAME"

/app/workspace/bin/migrate_up.sh --through 000_base_staging_schema
/app/workspace/bin/import_sources.sh
/app/workspace/bin/migrate_up.sh
python3 /app/workspace/bin/write_report.py
