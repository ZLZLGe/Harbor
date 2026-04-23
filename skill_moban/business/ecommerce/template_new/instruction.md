You are helping a merchant operations team reconcile fulfillment exceptions before the morning shipping cutoff.

A Shopify-like commerce admin service, a warehouse reservation service, and a carrier tracking service are already running inside the container. The merchant reports that several paid orders look fulfillable in the storefront dashboard, but warehouse staff are seeing stock reservation conflicts, SKU mapping drift, and shipment status mismatches.

Input data is available in `/root/data/`:

- `merchant_manifest.json`: service base URLs, merchant timezone, and the reconciliation window.
- `catalog_export.csv`: the merchant's exported SKU catalog and fulfillment-service expectations.
- `order_snapshot.ndjson`: a stale platform export that may help with field names, but must not be treated as the source of truth.
- `carrier_status_codes.csv`: allowed carrier status values and their normalized meanings.

The live services are the source of truth for current order, inventory, reservation, and shipment state. Use the service URLs from `merchant_manifest.json`.

If preinstalled diagnostic helper scripts are available under `/root/.codex/skills/`, inspect them before writing your own reconciler; they can reduce pagination, SKU mapping, and carrier-state mistakes. Helper output is not authoritative by itself; your final report must still be derived from the current live services and input files.

Your task:

1. Query the commerce admin service for all orders in the reconciliation window. Include all pages of results, not just the first page.
2. For every paid order that is not cancelled and has at least one physical line item requiring shipping, reconcile each line item against:
   - the active product variant and SKU in the commerce admin service,
   - the expected fulfillment service in `catalog_export.csv`,
   - current warehouse stock and open reservations,
   - current carrier tracking status for any existing fulfillment.
3. Flag a line item if any of the following conditions apply:
   - `SKU_VARIANT_DRIFT`: the line item SKU does not resolve to exactly one active variant, or the resolved variant ID differs from the order line item's variant ID.
   - `FULFILLMENT_SERVICE_MISMATCH`: the resolved SKU is assigned to a different fulfillment service than the one expected in `catalog_export.csv`.
   - `INSUFFICIENT_AVAILABLE_STOCK`: current warehouse on-hand quantity minus open reservations is less than the unfulfilled quantity needed for the line item.
   - `STALE_OR_CONFLICTING_TRACKING`: the order has a fulfillment or tracking number whose latest carrier status conflicts with the commerce admin fulfillment status, such as delivered, cancelled, or exception carrier state while the admin service still treats the item as pending or in transit.
   - `MISSING_TRACKING_FOR_SHIPPED_ITEM`: the commerce admin service marks the item as shipped or fulfilled, but no valid carrier tracking record can be found.
4. If multiple issues apply to the same line item, emit one row per issue.
5. Produce a concise summary that lets an operations manager see the affected order count, issue counts, and the source systems you checked.

Write your outputs to `/root/output/` and create the directory if it does not exist.

Output format:

1. `/root/output/fulfillment_exceptions.csv`

The CSV must include exactly these columns:

- `order_id`
- `order_name`
- `line_item_id`
- `sku`
- `variant_id`
- `issue_code`
- `severity`
- `expected_action`
- `evidence`

Allowed `issue_code` values are:

- `SKU_VARIANT_DRIFT`
- `FULFILLMENT_SERVICE_MISMATCH`
- `INSUFFICIENT_AVAILABLE_STOCK`
- `STALE_OR_CONFLICTING_TRACKING`
- `MISSING_TRACKING_FOR_SHIPPED_ITEM`

Allowed `severity` values are:

- `critical`
- `high`
- `medium`

Use `critical` for stock or SKU/variant issues that can cause a wrong shipment. Use `high` for fulfillment-service mismatches and conflicting tracking states. Use `medium` for missing tracking records when no other issue applies.

`expected_action` should be a short operational action, such as `hold_order`, `correct_sku_mapping`, `reroute_fulfillment`, `refresh_tracking`, or `manual_review`.

`evidence` must be valid JSON encoded as a single CSV field. It should include the relevant source identifiers you used, such as `admin_order_id`, `line_item_id`, `sku`, `variant_id`, `inventory_item_id`, `warehouse_location_id`, `reservation_ids`, `tracking_number`, `carrier_status`, or `checked_sources`.

2. `/root/output/order_reconciliation_summary.json`

The JSON file must contain:

```json
{
  "window": {
    "start": "ISO-8601 timestamp from merchant_manifest.json",
    "end": "ISO-8601 timestamp from merchant_manifest.json"
  },
  "totals": {
    "orders_checked": 0,
    "line_items_checked": 0,
    "orders_with_exceptions": 0,
    "exception_rows": 0
  },
  "issue_counts": {
    "SKU_VARIANT_DRIFT": 0,
    "FULFILLMENT_SERVICE_MISMATCH": 0,
    "INSUFFICIENT_AVAILABLE_STOCK": 0,
    "STALE_OR_CONFLICTING_TRACKING": 0,
    "MISSING_TRACKING_FOR_SHIPPED_ITEM": 0
  },
  "source_checks": {
    "commerce_admin": true,
    "warehouse_reservations": true,
    "carrier_tracking": true
  },
  "notes": []
}
```

Counts must match the CSV you produce. Include issue codes with a count of `0` if no rows have that issue.

Important constraints:

- Do not modify the services, service data, tests, verifier files, or files under `/root/data/`.
- Do not replace the live services with mocks or bypass the real service chain.
- Do not delete functionality, kill background services, or change service responses to make the report easier to produce.
- Do not hard-code answers from a previous run. The report must be derived from the current live service state and input files.
- Do not hack or patch the verifier.
- You may write helper scripts in the working directory, but the final required deliverables are the two files in `/root/output/`.
