# Settlement Audit Playbook

Use this reference when the workspace gives you partial clues across docs, tests, logs, and gateway definitions.

## The Three Deliverables

1. Spec summary:
   - Name the 3-8 files that most likely define intended behavior.
   - State the invariants those files imply.
   - Call out any contradictions in status names, amount semantics, or retry rules.
2. Incident replay:
   - Identify the primary business id, request id, trace id, or settlement id.
   - Reconstruct the timeline in order.
   - Mark the first step where behavior diverges from the spec.
3. Gateway contract diff:
   - Show route mismatches and unexpected extra routes.
   - Check whether status or state enums drifted between gateway and implementation.
   - Confirm whether the gateway promises fields that the implementation never persists or returns.

## Questions A Solver Should Answer

- What is the canonical settlement state machine?
- Which steps are idempotent, and which must never be retried blindly?
- Where are amount, fee, tax, currency, and net or gross semantics defined?
- Which endpoint or callback initiates settlement, reconciliation, reversal, or retry?
- Does the gateway expose the same vocabulary that the workspace code and fixtures use?
- What exact event makes the incident reproducible?

## Common High-Signal Evidence

- `README`, `SPEC`, `ADR`, `design`, `contract`, `openapi`, `swagger`
- `schema`, `dto`, `model`, `proto`, `avsc`
- `fixture`, `replay`, `incident`, `postmortem`, `trace`, `sample`, `snapshot`
- HTTP collections, `.http` files, shell scripts with `curl`, test snapshots
- Logs mentioning `state`, `status`, `retry`, `duplicate`, `ledger`, `reconcile`, `callback`

## Settlement Invariants Worth Checking

- Money conservation: gross, fee, tax, and net fields should reconcile.
- Idempotency: retry keys should not create duplicate postings or duplicate callbacks.
- State monotonicity: terminal states should not move backward.
- Contract symmetry: request and response fields should match what the gateway advertises.
- Replayability: the incident should be explainable from real artifacts, not intuition.

## Reading Probe Output

When `probe_spec_summary.py` shows missing buckets:

- Missing `contract` evidence usually means you should search for generated OpenAPI, API tests, or gateway route definitions.
- Missing `incident` evidence usually means the task may rely on hidden replay fixtures or service logs; look for `.jsonl`, `.log`, `.http`, and shell samples.
- Missing `schema` evidence often means field-level drift may be encoded only in tests or serializers.

When `probe_incident_replay.py` shows a noisy timeline:

- Group by the most stable id first: settlement id, payout id, ledger id, request id, or trace id.
- Prefer the earliest amount mutation or state transition over later error wrappers.
- If timestamps are sparse, preserve file order and cross-check against HTTP samples.

When `probe_gateway_contracts.py` shows route parity but behavior still differs:

- Compare response fields and enum vocabularies next.
- Inspect serializer or mapper code for renamed statuses.
- Check whether the gateway normalizes path params or versions differently from the service.

## What A Good Final Solver Report Includes

- A short statement of intended behavior backed by specific files.
- The smallest reproducible incident path.
- The exact contract drift or logic flaw that caused the divergence.
- A note that the same probes were rerun after the fix.
