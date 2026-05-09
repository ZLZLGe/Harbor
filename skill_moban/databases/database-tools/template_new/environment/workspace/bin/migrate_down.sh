#!/usr/bin/env bash

set -euo pipefail

source /app/workspace/bin/common.sh
/app/workspace/bin/start_postgres.sh >/dev/null

psql_db <<'SQL'
CREATE SCHEMA IF NOT EXISTS meta;
CREATE TABLE IF NOT EXISTS meta.schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
SQL

mapfile -t versions < <(
    psql_db -Atqc "
    SELECT version
    FROM meta.schema_migrations
    WHERE version > '000_base_staging_schema'
    ORDER BY version DESC
    "
)

for version in "${versions[@]}"; do
    [ -n "$version" ] || continue
    psql_db -f "/app/workspace/migrations/${version}.down.sql"
    psql_db -c "DELETE FROM meta.schema_migrations WHERE version = '$version'"
done
