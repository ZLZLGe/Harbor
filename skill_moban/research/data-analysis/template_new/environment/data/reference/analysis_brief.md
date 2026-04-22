# Board Analysis Brief

You are preparing the final board-review operating pack for the 2025 H1 growth review.

## What the board wants to know

1. Which segment/channel combinations actually drove the late-period change in net ARR?
2. Where are we buying volume that does not translate into healthy activation, retention, or payback?
3. Is there a specific regional or cohort concentration behind churn, downgrade pressure, or refund leakage?
4. Do support burden and product adoption explain why some cohorts underperform despite headline pipeline volume?

## Expectations

- Work at monthly grain.
- Use `segment` and `channel` as the primary reporting cuts.
- You may use region or cohort details inside the diagnosis, but the formal metric table must remain at `month x segment x channel` grain.
- Keep the final management summary concise, but evidence-based.
- Before final submission, you must call the live audit API in this order:
  1. `GET /manifest`
  2. `POST /validate-metrics`
  3. `POST /submit-report`
- If the optional helper bundle is mounted at `/app/.codex/skills/saas-board-metrics-diagnostics/`, prefer that workflow instead of inventing a separate local convention.

## Advice

- Do not rely on one table in isolation. The point of the task is to reconcile revenue movement, spend, activation, support load, and refunds into one coherent operating story.
- The strongest risk diagnosis usually needs a time-aligned evidence chain: monthly revenue movement, retention, support burden, and refund concentration should point to the same story.
- The best final answer is not the longest answer. It is the one where the metrics, the structured diagnosis, the summary, and the final submission all agree.
- Build `final_submission.json` from the saved deliverables, not from a separate in-memory object graph. In particular, the `metrics_snapshot` payload should come from re-reading `/app/output/metrics_snapshot.csv` with normal CSV semantics, so the saved bundle mirrors the on-disk artifact exactly.
- Some runtimes may also mount optional helper probes under `/app/.codex/skills/`. If they are present, you may use them to inspect the metric contract, diff your CSV against a raw-data recomputation, scan likely anomalies, and package the final bundle before submission.
- If the audit API is unavailable on the first request, verify the local service before falling back to assumptions. The service implementation lives at `/services/board-audit/server.py`; the live API remains part of the required chain, not an optional extra.
