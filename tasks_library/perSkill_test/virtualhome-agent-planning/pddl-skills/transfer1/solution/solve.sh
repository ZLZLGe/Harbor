#!/bin/bash
set -euo pipefail

PLANNING_BATCH_CONFIG=/root/warehouse_batch.json python3 /root/plan_batch.py
