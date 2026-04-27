# ClickHouse Delivery Wave Timezone Patterns

For this task family, avoid row-valued timezone arguments and avoid string
formatting for business dates. ClickHouse 25.x requires constant timezone
arguments for typed conversion functions such as `toTimeZone`.

Use a small constant dispatch that matches the warehouse reference data:

```sql
multiIf(
  timezone = 'America/Los_Angeles', toDate(toTimeZone(event_time, 'America/Los_Angeles')),
  timezone = 'America/New_York', toDate(toTimeZone(event_time, 'America/New_York')),
  timezone = 'America/Chicago', toDate(toTimeZone(event_time, 'America/Chicago')),
  timezone = 'Europe/London', toDate(toTimeZone(event_time, 'Europe/London')),
  timezone = 'Asia/Tokyo', toDate(toTimeZone(event_time, 'Asia/Tokyo')),
  toDate(event_time)
) AS business_date
```

Wave sessionization is usually easiest in three stages:

1. Deduplicate scans and compute each loaded scan's local `business_date`.
2. Use `lagInFrame(loaded_at_utc)` per `(warehouse_id, route_id, business_date)` to mark a new wave when the gap is greater than 20 minutes.
3. Use a cumulative `sum(is_new_wave)` in a wrapping query to assign a stable wave sequence, then compute wave boundaries with grouped aggregation.

Keep invalid final orders out of both wave metrics and the audit table. Compute
final order status with `argMax(status, tuple(event_time, event_version,
ingested_at))`.

For stockout exposure, build snapshot intervals with `leadInFrame(event_time)`
per `(warehouse_id, sku_id)`, keep only `available_to_promise <= 0`, and join
distinct `(wave_id, sku_id)` rows to those intervals. Sum
`dateDiff('minute', greatest(wave_start_utc, start_at), least(wave_end_utc,
end_at))` only for positive overlaps.
