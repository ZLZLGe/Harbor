#!/usr/bin/env bash

set -euo pipefail

source /app/workspace/bin/env.sh
/app/workspace/bin/start_postgres.sh

"${PSQL_BASE[@]}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" >/dev/null
"${PSQL_BASE[@]}" -d postgres -c "CREATE DATABASE ${DB_NAME};" >/dev/null
