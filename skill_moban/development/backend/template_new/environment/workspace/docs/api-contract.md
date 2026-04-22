# API Contract

Base URL: `http://127.0.0.1:8120`

## `POST /api/v1/holds`

Creates or replays a temporary inventory hold.

Headers:

- `Idempotency-Key` (required)

Request body:

```json
{
  "sku": "CHAIR-RED-001",
  "location": "store-nyc",
  "quantity": 2,
  "hold_seconds": 5,
  "customer_id": "cust-1001"
}
```

Response fields:

- `hold_id`
- `sku`
- `location`
- `quantity`
- `status`
- `expires_at`
- `idempotency_key`
- `replayed`

Expected behavior:

- Retrying the exact same payload with the same `Idempotency-Key` is safe.
- The retry must not create a second active reservation downstream.

## `GET /api/v1/holds/{hold_id}`

Returns the current public-service view of the hold.

## `GET /api/v1/availability?sku=...&location=...`

Response fields:

- `sku`
- `location`
- `on_hand`
- `safety_stock`
- `reserved`
- `available`

Expected behavior:

- `available = on_hand - safety_stock - reserved`
- `reserved` must reflect only currently blocking reservations for this `sku + location`
- Expired or cancelled holds must not continue blocking `available`

## `POST /api/v1/orders/confirm`

Request body:

```json
{
  "hold_id": "hold_...",
  "order_id": "order-9001"
}
```

Expected behavior:

- Only an active, unexpired hold can be confirmed.
- Confirmation permanently consumes stock and transitions the hold to `confirmed`.
- Confirming an expired hold must fail with a conflict-style error instead of silently succeeding.

## `POST /api/v1/orders/cancel`

Request body:

```json
{
  "hold_id": "hold_...",
  "reason": "customer-request"
}
```

Expected behavior:

- Cancel releases the reservation exactly once.
- Repeating a cancel for an already cancelled hold should be safe and leave the terminal state unchanged.
