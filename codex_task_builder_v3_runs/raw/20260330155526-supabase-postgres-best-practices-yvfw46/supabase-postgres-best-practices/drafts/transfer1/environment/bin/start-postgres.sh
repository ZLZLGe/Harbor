#!/bin/bash

set -euo pipefail

DATA_DIR=/tmp/worker-queue-pgdata
SOCKET_DIR=/tmp/worker-queue-pg
LOG_FILE=/tmp/worker-queue-postgres.log
PORT=55433

if pg_isready -h "$SOCKET_DIR" -p "$PORT" >/dev/null 2>&1; then
  exit 0
fi

mkdir -p "$DATA_DIR" "$SOCKET_DIR"
chown -R postgres:postgres "$DATA_DIR" "$SOCKET_DIR"

if [ ! -s "$DATA_DIR/PG_VERSION" ]; then
  su postgres -c "initdb -D '$DATA_DIR' >/tmp/worker-queue-initdb.log"
fi

rm -f "$SOCKET_DIR/.s.PGSQL.$PORT" "$SOCKET_DIR/.s.PGSQL.$PORT.lock"
su postgres -c "pg_ctl -D '$DATA_DIR' -l '$LOG_FILE' -o \"-F -k '$SOCKET_DIR' -p '$PORT'\" start"

for _ in $(seq 1 60); do
  if pg_isready -h "$SOCKET_DIR" -p "$PORT" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

echo "Postgres failed to start. See $LOG_FILE for details." >&2
exit 1
