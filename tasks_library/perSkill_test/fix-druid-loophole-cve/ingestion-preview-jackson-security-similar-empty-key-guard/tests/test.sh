#!/bin/bash

set -euo pipefail

WORKSPACE=${WORKSPACE:-/root}
SERVICE_DIR=${SERVICE_DIR:-${WORKSPACE}/preview-service}
PATCHES_DIR=${PATCHES_DIR:-${WORKSPACE}/patches}

mkdir -p /logs/verifier/patches

if [ -d "${PATCHES_DIR}" ]; then
  find "${PATCHES_DIR}" -maxdepth 1 -type f -name "*.patch" -exec cp {} /logs/verifier/patches/ \;
fi

cd "${SERVICE_DIR}"
git diff HEAD > /logs/verifier/patches/preview-service.diff || true

mvn -q clean package -DskipTests

pkill -f "com.harbor.preview.PreviewServer" 2>/dev/null || true
pkill -f "preview-service-1.0.0.jar" 2>/dev/null || true

nohup java -jar "${SERVICE_DIR}/target/preview-service-1.0.0.jar" > /tmp/preview-service.log 2>&1 &

for attempt in $(seq 1 30); do
  if curl -fsS "http://localhost:${PREVIEW_PORT:-8080}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

set +e
python3 /tests/test_outputs.py
status=$?
set -e

if [ ${status} -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
  cat /tmp/preview-service.log || true
fi

exit ${status}
