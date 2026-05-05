#!/usr/bin/env bash
set -euo pipefail

cd /app
pytest -q /app/tests/test_outputs.py /app/tests/test_guardrails.py
