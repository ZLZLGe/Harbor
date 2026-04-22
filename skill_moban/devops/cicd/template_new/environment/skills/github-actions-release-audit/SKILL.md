# github-actions-release-audit

Use this skill when a CI/CD task involves a GitHub Actions-style multi-stage release pipeline, local broker-backed release data, or bundle / promotion contract drift that is hard to see from raw files alone.

## What this skill is for

- Inspecting the workflow graph before editing it
- Replaying the release dry-run with consistent logs
- Comparing the generated bundle and promotion plan against the live broker contract
- Proving whether outputs still come from the real broker or from stale fallback snapshots

## Recommended workflow

1. Run `python /opt/task-skills/github-actions-release-audit/scripts/render_workflow_graph.py /app/workspace/.github/workflows/release-dry-run.yml`.
2. Run `python /opt/task-skills/github-actions-release-audit/scripts/replay_release_dry_run.py --workspace /app/workspace`.
3. Run `python /opt/task-skills/github-actions-release-audit/scripts/check_release_contract.py --workspace /app/workspace`.
4. Only then patch the workflow or release scripts.
5. Re-run the same probes after the fix.

## Guardrails

- Do not replace the broker with static JSON.
- Do not collapse the workflow into a single shell step.
- Do not treat every stable artifact as deployable without checking the release contract.
- `promote` is guardrail-sensitive: after the repair, it should depend on `attest` and not keep an extra `package` edge.
