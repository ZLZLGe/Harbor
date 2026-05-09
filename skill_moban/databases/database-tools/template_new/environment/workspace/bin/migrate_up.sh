#!/usr/bin/env bash

set -euo pipefail

source /app/workspace/bin/common.sh
/app/workspace/bin/start_postgres.sh >/dev/null

through_version=""
if [ "${1:-}" = "--through" ]; then
    through_version="${2:?missing version for --through}"
fi

psql_db <<'SQL'
CREATE SCHEMA IF NOT EXISTS meta;
CREATE TABLE IF NOT EXISTS meta.schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
SQL

for file in $(find /app/workspace/migrations -maxdepth 1 -type f -name '*.up.sql' | sort); do
    version="$(basename "$file" .up.sql)"
    if [ -n "$through_version" ] && [[ "$version" > "$through_version" ]]; then
        continue
    fi

    if psql_db -Atqc "SELECT 1 FROM meta.schema_migrations WHERE version = '$version'" | grep -q '^1$'; then
        continue
    fi

    psql_db -f "$file"
    psql_db -c "INSERT INTO meta.schema_migrations(version) VALUES ('$version')"
done
