---
name: saas-board-metrics-diagnostics
description: Standardize SaaS board-metrics contract checks, anomaly scanning, and final bundle submission against the live localhost audit API.
---

# SaaS Board Metrics Diagnostics

Use this skill when a task asks you to build a board-ready SaaS metrics bundle from frozen orders, subscriptions, marketing, product, and support data, especially when the task also requires a live `manifest -> validate-metrics -> submit-report` chain.

This skill does not give you a final answer. It helps you standardize the highest-risk parts of the workflow:

1. Probe the manifest and metric contract before writing outputs.
2. Recompute the published metric table from raw data and diff it against your current CSV.
3. Scan likely growth, risk, efficiency, and support-product signals from the raw data so you do not miss the real anomalies.
4. Canonicalize and submit the final bundle only after the standalone outputs agree with each other.

## Recommended Workflow

1. Read:
   - `/app/data/reference/analysis_brief.md`
   - `/app/data/reference/metric_contract.json`
2. Run:
   - `python /app/.codex/skills/saas-board-metrics-diagnostics/scripts/probe_metric_contract.py`
3. Build `metrics_snapshot.csv`.
4. Diff your metrics against the raw-data recomputation:
   - `python /app/.codex/skills/saas-board-metrics-diagnostics/scripts/recompute_metrics_diff.py /app/output/metrics_snapshot.csv`
5. Scan anomalies to guide `diagnosis_report.json` and `executive_summary.md`:
   - `python /app/.codex/skills/saas-board-metrics-diagnostics/scripts/scan_growth_signals.py`
6. After your standalone files exist, package and submit:
   - `python /app/.codex/skills/saas-board-metrics-diagnostics/scripts/package_and_submit_bundle.py`

## Guardrails

- Do not hardcode metric values, receipts, or anomaly rankings from the tests.
- Do not skip the live audit chain.
- Do not assume the final saved submission file matches what you posted; verify it explicitly.
- If `recompute_metrics_diff.py` reports mismatches, fix the metric logic first. Do not “patch” the diagnosis around bad metrics.

