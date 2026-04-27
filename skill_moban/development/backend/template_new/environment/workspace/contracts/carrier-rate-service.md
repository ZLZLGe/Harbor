# Carrier Rate Service Contract

Base URL: `http://127.0.0.1:9101`

## `POST /internal/rates`

Request JSON:

```json
{
  "originPostal": "94105",
  "destinationPostal": "10001",
  "weightGrams": 1200,
  "shipDate": "2026-05-04"
}
```

Response JSON:

```json
{
  "rates": [
    {
      "rateId": "rate_...",
      "carrier": "roadline",
      "serviceLevel": "standard",
      "amount": 1285,
      "currency": "USD",
      "etaMinDays": 3,
      "etaMaxDays": 5,
      "available": true
    }
  ]
}
```

The gateway is responsible for partner authorization, public quote IDs, pagination, sorting, and response envelopes.
