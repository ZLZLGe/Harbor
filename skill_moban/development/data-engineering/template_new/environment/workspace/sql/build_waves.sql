CREATE TABLE IF NOT EXISTS analytics.wave_metrics (
    warehouse_id String,
    route_id String,
    business_date Date,
    wave_id String,
    wave_start_utc DateTime64(3, 'UTC'),
    wave_end_utc DateTime64(3, 'UTC'),
    loaded_packages UInt64,
    valid_orders UInt64,
    delivered_packages UInt64,
    late_packages UInt64,
    missing_delivery_packages UInt64,
    stockout_impacted_packages UInt64,
    stockout_exposure_minutes Int64,
    late_rate Decimal(10, 4),
    wave_status String
) ENGINE = MergeTree()
ORDER BY (warehouse_id, route_id, business_date, wave_id);

CREATE TABLE IF NOT EXISTS analytics.longest_wave_per_route AS analytics.wave_metrics
ENGINE = MergeTree()
ORDER BY (warehouse_id, route_id, business_date, wave_id);

CREATE TABLE IF NOT EXISTS analytics.order_package_audit (
    order_id String,
    package_id String,
    warehouse_id String,
    route_id String,
    business_date Date,
    wave_id String,
    order_final_status String,
    loaded_at_utc DateTime64(3, 'UTC'),
    delivered_at_utc Nullable(DateTime64(3, 'UTC')),
    sla_deadline_utc DateTime64(3, 'UTC'),
    sla_status String,
    stockout_impacted UInt8
) ENGINE = MergeTree()
ORDER BY (warehouse_id, route_id, business_date, wave_id, package_id, loaded_at_utc);

CREATE TABLE IF NOT EXISTS analytics.data_quality_summary (
    payload String
) ENGINE = Memory;

TRUNCATE TABLE analytics.wave_metrics;
TRUNCATE TABLE analytics.longest_wave_per_route;
TRUNCATE TABLE analytics.order_package_audit;
TRUNCATE TABLE analytics.data_quality_summary;

-- Placeholder implementation. It intentionally ignores final order status,
-- scan deduplication, local business dates, stockout intervals, and SLA logic.
INSERT INTO analytics.wave_metrics
SELECT
    warehouse_id,
    route_id,
    toDate(event_time) AS business_date,
    concat(warehouse_id, '-', route_id, '-', toString(business_date), '-1') AS wave_id,
    min(event_time) AS wave_start_utc,
    max(event_time) AS wave_end_utc,
    count() AS loaded_packages,
    uniqExact(order_id) AS valid_orders,
    CAST(0 AS UInt64) AS delivered_packages,
    CAST(0 AS UInt64) AS late_packages,
    CAST(0 AS UInt64) AS missing_delivery_packages,
    CAST(0 AS UInt64) AS stockout_impacted_packages,
    CAST(0 AS Int64) AS stockout_exposure_minutes,
    toDecimal64(0, 4) AS late_rate,
    'placeholder' AS wave_status
FROM raw.package_scans
WHERE scan_type = 'LOADED_ON_TRUCK'
GROUP BY warehouse_id, route_id, business_date;

INSERT INTO analytics.longest_wave_per_route
SELECT * FROM analytics.wave_metrics;

INSERT INTO analytics.data_quality_summary
SELECT '{}';
