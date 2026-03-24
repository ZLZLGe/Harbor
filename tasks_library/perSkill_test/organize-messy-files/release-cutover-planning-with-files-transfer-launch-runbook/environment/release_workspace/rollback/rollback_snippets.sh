#!/bin/bash

# Application rollback
deployctl rollback checkout-api --to 2026.04.01-rc1
deployctl rollback customer-portal --to 2026.04.01-rc1

# Safety switches
flagctl disable ledger_dual_write --env prod
flagctl disable express_wallet --env prod

# Data-plane fallback
workerctl resume billing-worker --profile stable
dbsnap restore payments --snapshot release_cutover_pre_20260408
