---
name: inventory-hold-debugging
description: Use when a backend inventory or checkout service shows duplicate reservations, stale availability after expiry, or inconsistent confirm/cancel transitions against a real downstream ledger.
---

# Inventory Hold Debugging

This skill helps diagnose inventory-hold consistency bugs without bypassing the real chain. It is designed for services that:

- accept idempotent hold requests,
- depend on a downstream inventory ledger or reservation service,
- maintain some local read model or hold table,
- can drift when retries, expiry, and terminal transitions interact.

## Use This Skill When

- The same hold request appears safe to retry but inventory still drops twice.
- Availability stays blocked after a TTL has elapsed.
- A hold can be confirmed or cancelled from an invalid state.
- You need to determine whether the bug lives in the public API, the local state model, or the downstream ledger interaction.

## Core Invariants

For a given `sku + location`, these invariants must hold:

1. A safe retry with the same `Idempotency-Key` produces at most one active downstream reservation.
2. Only active, unexpired holds block availability.
3. `confirmed` and `cancelled` are terminal states.
4. An expired hold cannot later become `confirmed`.
5. Public availability must converge to the downstream ledger truth after state reconciliation.

## Recommended Workflow

1. Reset the stack to a known baseline.
2. Replay one frozen scenario from `/app/workspace/data/replay/`.
3. For expiry bugs, prefer `expiry_then_cancel.json`, then inspect invariants before issuing any extra public API request.
4. Compare local hold state against the downstream ledger snapshot.
5. Identify whether the mismatch comes from:
   - duplicate downstream calls,
   - stale local hold status,
   - wrong availability aggregation,
   - invalid transition handling around expiry,
   - missing or half-written local rows after a downstream hold already exists.
6. After each code change, rerun the same replay and confirm the invariant failure is gone without regressing another path.

## Useful Commands

Reset both public and downstream state:

```bash
python "$CODEX_HOME/skills/inventory-hold-debugging/scripts/reset_stack.py"
```

Replay a frozen scenario:

```bash
python "$CODEX_HOME/skills/inventory-hold-debugging/scripts/run_replay.py" \
  /app/workspace/data/replay/hold_retry.json
```

Inspect local-vs-ledger drift:

```bash
python "$CODEX_HOME/skills/inventory-hold-debugging/scripts/inspect_invariants.py"
```

If `$CODEX_HOME` is not set, resolve the script path relative to this `SKILL.md` file before falling back to any hard-coded home directory.

Expiry-specific drift check:

```bash
python "$CODEX_HOME/skills/inventory-hold-debugging/scripts/reset_stack.py"
python "$CODEX_HOME/skills/inventory-hold-debugging/scripts/run_replay.py" \
  /app/workspace/data/replay/expiry_then_cancel.json
python "$CODEX_HOME/skills/inventory-hold-debugging/scripts/inspect_invariants.py"
```

## What To Look For

- Downstream ledger contains more active leases than the public service has active holds.
- An idempotency record points to a `hold_id` that no longer exists in SQLite.
- Local `expires_at` has passed but the hold still remains `active` in SQLite.
- Local rows only flip to `expired` after a later read request instead of converging on their own.
- Availability is derived from a stale local total instead of the reconciled ledger state.
- Confirmation logic ignores a downstream expiry conflict and still marks the hold `confirmed`.

## Guardrails

- Do not replace the downstream ledger with a mock.
- Do not hardcode fixed availability or terminal states.
- Do not remove hold expiry, idempotency, confirm, or cancel semantics to make tests pass.
- Any temporary probes should lead back to a real code fix in `/app/workspace/checkout-api/`.
