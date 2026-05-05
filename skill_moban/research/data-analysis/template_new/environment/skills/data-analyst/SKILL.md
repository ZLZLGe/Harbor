---
name: data-analyst
description: Use this skill for promotion, retail, or operations analytics tasks where raw event data must be converted into auditable business metrics.
---

# data-analyst

Use this skill for promotion, retail, or operations analytics tasks where raw event data must be converted into auditable business metrics.

## Diagnostic Workflow

1. Start from the business question and output contract. For this task the contract is the set of files under `/root/answer`.
2. Build metrics from raw event tables, not from `broken_outputs` or partially generated reports.
3. Deduplicate POS events by choosing the latest row per `order_id`, ordered by `event_at_utc`, then `ingested_at_utc`, then `event_id`.
4. Convert timestamps into each store's IANA timezone before deriving `business_date`.
5. Compute baseline and promotion windows from local business dates.
6. Join external factors before classifying performance:
   - weather anomaly
   - holiday
   - traffic index
   - stockout exposure hours
7. Keep both baseline and adjusted views in diagnostics. A promotion can look positive in the baseline view and fail after adjustment.
8. Call the local enrichment service for final labels and summaries instead of inventing them.

## Probe

This skill ships a deterministic probe that computes the expected analysis from the raw inputs without static answer files:

```bash
python /root/.codex/skills/data-analyst/promo_analysis_core.py --output /tmp/promo_probe
```

Use the probe as a diagnostic reference while repairing `/root/environment/pipeline/run_analysis.py`. A robust fix can copy or adapt the probe logic, but the final command must still be:

```bash
python /root/environment/pipeline/run_analysis.py --output /root/answer
```

## Common Failure Modes

- UTC grouping shifts New York and California transactions across business dates.
- Counting duplicate POS rows inflates revenue and units.
- Treating returned or cancelled latest order states as completed creates false uplift.
- Counting stockout events instead of clipped interval hours misses real promotion exposure.
- Reusing baseline uplift as adjusted ROI ignores spend, margin, traffic, holidays, weather, and stockout penalties.
- Writing the figure CSVs independently from the tables creates inconsistent reports.
