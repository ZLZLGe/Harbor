When the checkout service shows duplicate reservations, stale availability after expiry, or local-vs-ledger drift, use the `inventory-hold-debugging` skill from `~/.codex/skills/inventory-hold-debugging` before editing.

Recommended flow:

1. Reset the stack with the skill reset script.
2. Replay one frozen scenario from `/app/workspace/data/replay/`.
3. Run the invariant inspector to compare SQLite state with the downstream ledger.
4. Only then patch the formal service code in `/app/workspace/checkout-api/`.

Do not bypass the real `inventory-ledger` service.
