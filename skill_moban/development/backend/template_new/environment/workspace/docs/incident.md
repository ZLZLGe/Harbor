# Incident Summary

Service: `checkout-api`

Downstream dependency: local `inventory-ledger`

Date of frozen replay set: `2026-04-16`

## Reported symptoms

1. Mobile clients sometimes retry `POST /api/v1/holds` after a gateway timeout. Support reports that the repeated request often returns the same `hold_id`, but availability still drops twice.
2. Some holds stop the customer from checking out after their TTL has already elapsed. Operations can see the hold as effectively expired in the ledger, while the customer-facing availability endpoint still says the item is unavailable.
3. Customer support has screenshots of an order confirmation succeeding right after a hold should have expired. The resulting state is hard to unwind because downstream stock no longer matches the public API view.
4. During one deploy rollback, support also saw a retry return a server error even though the downstream ledger still showed an active lease for that checkout flow. The team suspects local persistence and downstream reservation can occasionally get out of sync during interrupted writes.

## Business constraints

- A hold is a temporary reservation and must not permanently reduce `on_hand`.
- `Idempotency-Key` exists so the client can safely retry the same hold request without double-reserving stock.
- `confirmed` and `cancelled` are terminal states.
- An expired hold must not be confirmable.
- Availability is per `sku + location`.
- Safety stock must remain protected.

## Existing runtime notes

- The public service uses `/app/workspace/state/checkout.db` for local hold state.
- The downstream ledger runs on `http://127.0.0.1:8131`.
- The public service is usually started with:

```bash
uvicorn checkout_api.main:app --host 127.0.0.1 --port 8120 --app-dir /app/workspace/checkout-api
```

- The replay payloads in `/app/workspace/data/replay/` were captured from real integration investigations and are frozen for deterministic debugging.
