You are building a partner-facing shipping API facade. The workspace is at `/app/workspace/` and contains an incomplete backend API gateway, deterministic input data, and two local downstream HTTP services that run inside the same container.

Input data is in:

- `/app/workspace/data/orders.ndjson`: order records, one JSON object per line.
- `/app/workspace/data/partners.json`: partner API keys, permissions, and rate-limit tiers.
- `/app/workspace/data/postal_zones.csv`: postal-code zone metadata.
- `/app/workspace/contracts/`: public contracts for the local carrier rate service and shipment booking service.
- `/app/workspace/gateway/`: the API gateway code you may modify.

Your task:

1. Implement `GET /api/v1/shipping-quotes`.

   The endpoint must accept these query parameters:

   - `originPostal`: origin postal code, required.
   - `destinationPostal`: destination postal code, required.
   - `weightGrams`: positive integer, required.
   - `shipDate`: date in `YYYY-MM-DD` format, required.
   - `serviceLevel`: optional, one of `standard`, `expedited`, `overnight`.
   - `carrier`: optional carrier filter.
   - `page[limit]`: optional, default `20`, maximum `50`.
   - `page[cursor]`: optional opaque cursor for the next page.
   - `sort`: optional, one of `price`, `-price`, `eta`, `-eta`.

   The gateway must call the local carrier rate service, combine the returned carrier quotes, and expose them through one stable public API shape. Exclude unavailable routes, overweight routes, and quotes that the authenticated partner is not allowed to use. If an authenticated partner explicitly requests a service level or carrier it is not allowed to use, return `403`.

2. Implement `POST /api/v1/shipments`.

   The endpoint creates a shipment from a quote returned by `GET /api/v1/shipping-quotes`. The request must include an `Idempotency-Key` header. The JSON body must contain:

   - `quoteId`: quote ID from the quote endpoint, required.
   - `orderId`: order ID from `/app/workspace/data/orders.ndjson`, required.
   - `labelFormat`: one of `pdf`, `zpl`, required.
   - `metadata`: optional object, returned unchanged in later shipment reads.

   A first successful create must return `201` with a `Location` header. A repeated request from the same partner with the same `Idempotency-Key` and identical body must return the same shipment result without creating another downstream booking. Reusing the same idempotency key with a different body must return `409`.

3. Implement `GET /api/v1/shipments/:shipmentId`.

   Return a previously created shipment only to the partner that created it. For a missing shipment or a shipment owned by another partner, return `404` without revealing which case occurred.

4. Implement authentication and partner rate limits.

   Requests authenticate with `X-Partner-Key`. Partner configuration comes from `/app/workspace/data/partners.json`. A missing or invalid key returns `401`. If a partner exceeds its configured limit, return `429` with `Retry-After`.

   Every authenticated response, including successful responses and rate-limit errors, must include standard production API rate-limit headers:

   - `X-RateLimit-Limit`: the partner's configured request limit for the current window.
   - `X-RateLimit-Remaining`: remaining requests in the current window after the current request is counted.
   - `X-RateLimit-Reset`: Unix timestamp when the current window resets.

5. Implement the response contract.

   Every successful response must use this envelope:

   ```json
   {
     "data": {},
     "meta": {},
     "links": {}
   }
   ```

   For list responses:

   - `data` is an array.
   - `meta.count` is the number of records in the current page.
   - `meta.hasMore` shows whether another page exists.
   - `links.self` is the current request path and query string.
   - `links.next` is present only when another page exists and must include `page[cursor]`.

   Every error response must use this envelope:

   ```json
   {
     "error": {
       "code": "string_code",
       "message": "human readable message",
       "details": []
     }
   }
   ```

   Use these status codes consistently:

   - `400`: malformed JSON or syntactically unparseable query input.
   - `401`: missing or invalid API key.
   - `403`: authenticated partner is not allowed to use the requested capability or resource class.
   - `404`: shipment not found or not accessible.
   - `409`: idempotency key conflict.
   - `422`: semantically invalid fields, such as non-positive weight, invalid date, or unknown enum.
   - `429`: partner rate limit exceeded.
   - `502`: downstream service returned an unavailable or invalid response.
   - `503`: downstream service timed out or is temporarily unavailable; include `Retry-After`.

Output format:

The output is the running HTTP API behavior, not a separate file. The verifier will start `/app/workspace/run.sh` and make real HTTP requests to the gateway. It will check response bodies, status codes, headers, pagination links, idempotency behavior, resource isolation, rate limiting, and downstream side effects.

Example quote response:

```json
{
  "data": [
    {
      "quoteId": "qt_...",
      "carrier": "roadline",
      "serviceLevel": "standard",
      "price": {
        "amount": 1285,
        "currency": "USD"
      },
      "eta": {
        "minDays": 3,
        "maxDays": 5
      },
      "expiresAt": "2026-05-04T12:00:00Z"
    }
  ],
  "meta": {
    "count": 1,
    "hasMore": false
  },
  "links": {
    "self": "/api/v1/shipping-quotes?originPostal=94105&destinationPostal=10001&weightGrams=1200&shipDate=2026-05-04"
  }
}
```

Example error response:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [
      {
        "field": "weightGrams",
        "code": "must_be_positive",
        "message": "weightGrams must be a positive integer"
      }
    ]
  }
}
```

Notes:

- You may modify files under `/app/workspace/gateway/`.
- You may add gateway-internal modules, persistence files, or tests if useful.
- Do not modify `/app/workspace/data/`.
- Do not modify `/app/workspace/contracts/`.
- Do not modify, replace, or disable the local carrier rate service or shipment booking service.
- Do not modify verifier files, task metadata, environment skills, or hidden evaluation files.
- Do not hard-code verifier requests, return static answers, detect the test process, bypass the real HTTP downstream services, remove features, disable authentication, disable rate limiting, or weaken the business rules to make tests pass.
