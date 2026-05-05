#!/bin/bash
set -euo pipefail

mkdir -p /app/runtime/logs

if [ -f /app/runtime/feed-server.pid ]; then
  pid="$(cat /app/runtime/feed-server.pid)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    exit 0
  fi
fi

cd /app/data/mirror/site
python3 -m http.server 8765 --bind 127.0.0.1 >/app/runtime/logs/feed-server.log 2>&1 &
echo $! > /app/runtime/feed-server.pid
sleep 1
curl -fsS http://127.0.0.1:8765/feeds/github-changelog.xml >/dev/null
