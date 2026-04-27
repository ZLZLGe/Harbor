# Shipment Booking Service Contract

Base URL: `http://127.0.0.1:9102`

## `POST /internal/bookings`

Request JSON:

```json
{
  "partnerId": "partner_alpha",
  "orderId": "ord_alpha_1001",
  "quote": {
    "quoteId": "qt_...",
    "carrier": "roadline",
    "serviceLevel": "standard"
  },
  "labelFormat": "pdf",
  "metadata": {}
}
```

Response JSON:

```json
{
  "shipmentId": "shp_...",
  "trackingNumber": "TRK...",
  "labelUrl": "https://labels.local/shp_....pdf"
}
```

The booking service is not idempotent. The gateway must enforce idempotency before calling this service.
