#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
BUNDLE_PATH="$DIST_DIR/harbor-release-bundle.tgz"

mkdir -p "$DIST_DIR"

python3 "$ROOT_DIR/scripts/build_release_bundle.py" \
  --repo-root "$ROOT_DIR" \
  --dockerfile "$ROOT_DIR/Dockerfile" \
  --output "$BUNDLE_PATH"

tar -tzf "$BUNDLE_PATH" | grep -q '^release/release-manifest.json$'
tar -tzf "$BUNDLE_PATH" | grep -q '^release/entrypoint.sh$'
tar -tzf "$BUNDLE_PATH" | grep -q '^app/main.py$'
