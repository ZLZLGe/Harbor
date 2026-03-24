#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
dev-bootstrap --seed data/bootstrap_seed.json --output var/bootstrap_report.txt
