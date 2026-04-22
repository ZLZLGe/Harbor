---
name: settlement-quality-audit
description: Use when a settlement or reconciliation task needs fast evidence gathering across specs, incident artifacts, and gateway contracts before fixing code-quality or behavioral drift.
allowed-tools: Read Write Edit Bash
license: MIT
---

# Settlement Quality Audit

This skill is for code-quality tasks where the hard part is not writing the patch, but first proving what the settlement flow is supposed to do, what actually happened in a broken incident, and whether the gateway contract still matches the implementation.

It is especially useful when a task involves any of these themes:

- settlement, payout, remittance, refund, reversal, chargeback, or reconciliation flows,
- gateway-to-service drift around request shape, endpoint behavior, or state enums,
- incident timelines reconstructed from logs, fixtures, or replay samples,
- ambiguous specs spread across Markdown, OpenAPI, JSON schemas, ADRs, or tests.

## What This Skill Produces

Use the bundled probes to assemble three outputs before editing code:

1. A spec summary with the most relevant source files and the invariants they imply.
2. An incident replay timeline with ids, state transitions, amount signals, and replayable HTTP clues.
3. A gateway contract diff showing route drift and suspicious state-vocabulary mismatches.

## Recommended Workflow

Run these commands from the environment root or any working directory:

```bash
python3 "$CODEX_HOME/skills/settlement-quality-audit/scripts/probe_spec_summary.py"
python3 "$CODEX_HOME/skills/settlement-quality-audit/scripts/probe_incident_replay.py"
python3 "$CODEX_HOME/skills/settlement-quality-audit/scripts/probe_gateway_contracts.py"
```

If `$CODEX_HOME` is not set, resolve the script paths relative to this `SKILL.md`. In this template package, the probes are also available next to the environment under:

```bash
python3 ./scripts/probe_spec_summary.py
python3 ./scripts/probe_incident_replay.py
python3 ./scripts/probe_gateway_contracts.py
```

When the workspace is large, start with tighter scopes:

```bash
python3 ./scripts/probe_spec_summary.py --limit 12
python3 ./scripts/probe_incident_replay.py --focus-id settlement_123 --limit-events 30
python3 ./scripts/probe_gateway_contracts.py --gateway-root /services/settlement-gateway --show-matches
```

## Core Invariants To Validate

1. A settlement instruction should have one unambiguous state machine, even if multiple documents describe it.
2. Retries must not duplicate money movement, ledger writes, or callback side effects.
3. Amount, currency, fee, and net or gross semantics must stay consistent across gateway, service, and replay artifacts.
4. Gateway contract and implementation must agree on endpoint shape, method, and terminal states.
5. Incident evidence should be explainable by the documented spec, not by accidental fallback behavior or undocumented local patches.

## Probe Guide

- `probe_spec_summary.py`: scans the environment for specs, ADRs, schemas, OpenAPI files, test fixtures, and incident notes, then prints a solver-ready summary of the strongest evidence.
- `probe_incident_replay.py`: reconstructs a timeline from JSON, JSONL, log, HTTP, shell, and text artifacts; surfaces candidate ids, state transitions, amount changes, and replay steps.
- `probe_gateway_contracts.py`: compares gateway-facing contracts against workspace implementation patterns to reveal missing routes, extra routes, and enum or state drift.

## How To Use The Output

- Start your write-up with the spec summary so the final fix is grounded in explicit evidence.
- Use the replay output to identify the first divergence between expected and observed behavior.
- Use the contract diff to decide whether the fix belongs in the gateway, the downstream service, or both.
- Re-run the same probes after the patch and confirm the narrative became simpler, not just quieter.
- Before finishing, verify the final `export_summary.md` explicitly names both formal scenarios and that the code-review runbook captures risk plus evidence, not just generic advice.

## Reference

Read [references/settlement-audit-playbook.md](references/settlement-audit-playbook.md) before patching. It contains a compact checklist for turning probe output into a reliable solver report.

## Guardrails

- Do not replace the gateway or ledger boundary with static fake data just to make the task easier.
- Do not assume the first spec file is canonical; compare docs, fixtures, and contracts.
- Do not collapse distinct terminal states such as `failed`, `reversed`, `cancelled`, or `settled` without evidence.
- Do not stop at route parity if field-level semantics or state vocabulary still disagree.
