---
name: clickhouse-io-codex
description: Use when repairing a local ClickHouse analytics pipeline over parquet and csv inputs, especially if you need to diagnose schema drift, keep cleaning rules aligned with the explicit business contract, preserve valid zone-lookup rows including literal N/A values, and verify month-partitioned ranking outputs directly in ClickHouse tables.
metadata:
  short-description: ClickHouse pipeline repair workflow for Codex
---

# ClickHouse IO Codex Companion

This companion wrapper exists because Codex requires YAML frontmatter on discoverable skills.
The canonical source skill remains `../clickhouse-io/SKILL.md`; do not modify that file.

## Workflow

1. Read `../clickhouse-io/SKILL.md` first for the base ClickHouse table-design and analytics guidance.
2. Start from the real execution path:
   - `run_pipeline.sh`
   - loader shell / SQL files actually invoked by that script
   - ClickHouse tables materialized by the pipeline
3. Check multi-file ingestion before touching downstream aggregates:
   - both monthly parquet inputs must load
   - column name drift can be case-sensitive
   - swallowed loader failures usually create misleading downstream counts
4. Match cleaning rules to the task contract exactly. Do not invent stricter filters unless the contract requires them.
   - keep rows with `trip_distance >= 0`
   - keep rows with `fare_amount >= 0`
   - keep rows with `total_amount >= 0`
   - keep mapped zone rows even when the literal value is `N/A`, as long as the lookup row exists
   - `avg_tip_pct` is a ratio, not a percent multiplier
5. For route-ranking outputs, validate the window logic in ClickHouse itself:
   - ranking must partition by `service_month`
   - keep the top 20 routes for each month, not top 20 globally
6. After edits, rerun `./run_pipeline.sh` and verify with ClickHouse queries:
   - `uniqExact(source_month)` in `analytics.trips_raw` is `2`
   - `analytics.top_zone_routes` has `20` rows for `2023-01-01`
   - `analytics.top_zone_routes` has `20` rows for `2023-02-01`
   - `output/summary.json` reflects the rerun, not a cached file
