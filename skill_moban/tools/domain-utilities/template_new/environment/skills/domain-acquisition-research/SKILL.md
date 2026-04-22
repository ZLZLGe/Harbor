---
name: domain-acquisition-research
description: Standardize manifest probing, snapshot gathering, score recomputation, and evidence packaging for frozen domain acquisition research tasks.
---

# Domain Acquisition Research

Use this skill when a task asks you to evaluate a fixed domain candidate pool and produce a structured acquisition recommendation backed by market, archive, authority, legal, and localhost snapshot evidence.

This skill does not give you the final answer. It helps you standardize the highest-risk parts of the workflow:

1. Probe the localhost manifest before writing outputs.
2. Pull and inspect per-domain frozen snapshots from the documented lookup service.
3. Recompute scores against the published policy so you can catch formula drift early.
4. Package evidence in a consistent machine-readable format for the final report.

## Recommended Workflow

1. Read:
   - `/app/data/market_brief.md`
   - `/app/data/scoring_policy.md`
   - `/app/data/service_catalog.md`
2. Run:
   - `python /app/.codex/skills/domain-acquisition-research/scripts/probe_manifest.py`
3. Inspect local snapshots:
   - `python /app/.codex/skills/domain-acquisition-research/scripts/pull_domain_snapshot.py dispatchpilot.com`
4. Build or update your report draft.
5. Diff your current output against the scoring policy:
   - `python /app/.codex/skills/domain-acquisition-research/scripts/recompute_domain_scores.py`
6. Run the preflight contract check before finalizing:
   - `python /app/.codex/skills/domain-acquisition-research/scripts/validate_report_contract.py`
7. Package evidence consistently before finalizing:
   - `python /app/.codex/skills/domain-acquisition-research/scripts/package_report_stub.py`

## Canonical Evidence Shape

For each domain, the final report should preserve at least these machine-readable evidence fields when they are available:

- `candidate_domains.csv` / `keyword_alignment`
- `authority_metrics.csv` / `referring_domains`
- `local_snapshot_api` / `listing_state`
- `trademark_flags.csv` / `risk_summary`

You may add richer evidence, but do not replace these canonical anchors with only free-form summaries or absolute file paths.

## Guardrails

- Do not hardcode the final top pick or top three from memory.
- Do not ignore legal risk, archive mismatch, or price ceilings just because market-fit numbers look good.
- Do not delete candidates to make ranking easier.
- If the recomputation script or preflight validator reports drift, fix the underlying logic instead of patching only the final ranking.
