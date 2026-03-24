#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

cd /app/workspace
patch -p1 < "$SCRIPT_DIR/fix.patch"
