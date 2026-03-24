#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

for version in 3.10 3.11; do
    echo "==> Running unit-tests (python-${version})"
    PYTHONPATH="$ROOT_DIR/src" MATRIX_PYTHON_VERSION="$version" python -m unittest -v tests.test_summary
done
