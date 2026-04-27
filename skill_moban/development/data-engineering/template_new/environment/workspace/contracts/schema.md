# Delivery Wave Data Contract

All timestamps are UTC unless a field name explicitly ends with `_local`.

## package_scans

`scan_id, package_id, order_id, warehouse_id, route_id, sku_id, scan_type, event_time, ingested_at`

Valid `scan_type` values are `LOADED_ON_TRUCK`, `DELIVERED`, `AT_SORT`, and `EXCEPTION`.

## order_events

JSON lines with `order_id`, `status`, `event_time`, `event_version`, and `ingested_at`.

Final invalid statuses are `CANCELLED`, `PAYMENT_FAILED`, and `FRAUD_REJECTED`.

## inventory_snapshots

`snapshot_id, warehouse_id, sku_id, available_to_promise, event_time, ingested_at`

Rows are point-in-time states. A state remains active until the next snapshot for the same `(warehouse_id, sku_id)`.

## reference

- `warehouses.csv`: `warehouse_id`, `region`, `timezone`
- `route_sla.csv`: `warehouse_id`, `route_id`, `sla_minutes`
- `skus.csv`: `sku_id`, `product_family`, `active`
