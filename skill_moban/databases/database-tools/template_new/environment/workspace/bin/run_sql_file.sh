#!/usr/bin/env bash

set -euo pipefail

source /app/workspace/bin/env.sh

if [ "$#" -ne 1 ]; then
    echo "usage: run_sql_file.sh <file>" >&2
    exit 1
fi

"${PSQL_BASE[@]}" -d "$DB_NAME" -f "$1"
