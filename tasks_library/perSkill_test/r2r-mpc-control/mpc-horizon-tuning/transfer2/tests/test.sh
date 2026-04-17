#!/bin/bash
set -euo pipefail
python -m pytest -q /tests/test_outputs.py
