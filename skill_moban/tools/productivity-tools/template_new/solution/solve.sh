#!/bin/bash
set -euo pipefail

export PYTHONPATH="/solution:/tests${PYTHONPATH:+:$PYTHONPATH}"
python3 /solution/create_digest.py
