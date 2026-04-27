#!/usr/bin/env bash
set -euo pipefail

cat > /app/workspace/sql/build_waves.sql <<'SQL'
-- delivery-wave-clickhouse-io-scaffold
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

CREATE TABLE IF NOT EXISTS analytics.longest_wave_per_route (
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

CREATE TEMPORARY TABLE scans_dedup AS
SELECT
    scan_id,
    package_id,
    order_id,
    warehouse_id,
    route_id,
    sku_id,
    scan_type,
    event_time,
    ingested_at
FROM
(
    SELECT
        *,
        row_number() OVER (PARTITION BY scan_id ORDER BY ingested_at DESC, event_time DESC) AS rn
    FROM raw.package_scans
)
WHERE rn = 1;

CREATE TEMPORARY TABLE final_orders AS
SELECT
    order_id,
    argMax(status, tuple(event_time, event_version, ingested_at)) AS order_final_status
FROM raw.order_events
GROUP BY order_id;

CREATE TEMPORARY TABLE delivered_packages AS
SELECT
    package_id,
    min(event_time) AS delivered_at_utc
FROM scans_dedup
WHERE scan_type = 'DELIVERED'
GROUP BY package_id;

CREATE TEMPORARY TABLE stockout_intervals AS
SELECT
    warehouse_id,
    sku_id,
    start_at,
    end_at
FROM
(
    SELECT
        i.warehouse_id,
        i.sku_id,
        i.available_to_promise,
        i.event_time AS start_at,
        leadInFrame(i.event_time) OVER (
            PARTITION BY i.warehouse_id, i.sku_id
            ORDER BY i.event_time, i.ingested_at, i.snapshot_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS end_at
    FROM
    (
        SELECT *
        FROM
        (
            SELECT
                *,
                row_number() OVER (PARTITION BY snapshot_id ORDER BY ingested_at DESC, event_time DESC) AS rn
            FROM raw.inventory_snapshots
        )
        WHERE rn = 1
    ) AS i
    INNER JOIN raw.skus AS sku ON sku.sku_id = i.sku_id AND sku.active = 1
)
WHERE available_to_promise <= 0 AND end_at > start_at;

CREATE TEMPORARY TABLE load_base AS
SELECT
    s.scan_id AS scan_id,
    s.package_id AS package_id,
    s.order_id AS order_id,
    s.warehouse_id AS warehouse_id,
    s.route_id AS route_id,
    s.sku_id AS sku_id,
    s.event_time AS loaded_at_utc,
    multiIf(
        w.timezone = 'America/Los_Angeles', toDate(toTimeZone(s.event_time, 'America/Los_Angeles')),
        w.timezone = 'America/New_York', toDate(toTimeZone(s.event_time, 'America/New_York')),
        w.timezone = 'America/Chicago', toDate(toTimeZone(s.event_time, 'America/Chicago')),
        w.timezone = 'Europe/London', toDate(toTimeZone(s.event_time, 'Europe/London')),
        w.timezone = 'Asia/Tokyo', toDate(toTimeZone(s.event_time, 'Asia/Tokyo')),
        toDate(s.event_time)
    ) AS business_date,
    f.order_final_status,
    nullIf(toNullable(d.delivered_at_utc), toDateTime64('1970-01-01 00:00:00', 3, 'UTC')) AS delivered_at_utc,
    sla.sla_minutes,
    CAST(if(f.order_final_status NOT IN ('CANCELLED', 'PAYMENT_FAILED', 'FRAUD_REJECTED'), 1, 0) AS UInt8) AS is_valid_order
FROM scans_dedup AS s
INNER JOIN final_orders AS f ON f.order_id = s.order_id
INNER JOIN raw.warehouses AS w ON w.warehouse_id = s.warehouse_id
INNER JOIN raw.route_sla AS sla ON sla.warehouse_id = s.warehouse_id AND sla.route_id = s.route_id
LEFT JOIN delivered_packages AS d ON d.package_id = s.package_id
WHERE s.scan_type = 'LOADED_ON_TRUCK';

CREATE TEMPORARY TABLE wave_numbered AS
SELECT
    *,
    sum(is_new_wave) OVER (
        PARTITION BY warehouse_id, route_id, business_date
        ORDER BY loaded_at_utc, package_id, scan_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS wave_seq
FROM
(
    SELECT
        *,
        if(
            prev_loaded_at IS NULL OR dateDiff('second', prev_loaded_at, loaded_at_utc) > 1200,
            1,
            0
        ) AS is_new_wave
    FROM
    (
        SELECT
            *,
            lagInFrame(loaded_at_utc) OVER (
                PARTITION BY warehouse_id, route_id, business_date
                ORDER BY loaded_at_utc, package_id, scan_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
            ) AS prev_loaded_at
        FROM load_base
    )
);

CREATE TEMPORARY TABLE wave_loads AS
SELECT
    *,
    concat(warehouse_id, '-', route_id, '-', toString(business_date), '-', toString(wave_seq)) AS wave_id,
    min(loaded_at_utc) OVER (PARTITION BY warehouse_id, route_id, business_date, wave_seq) AS wave_start_utc,
    max(loaded_at_utc) OVER (PARTITION BY warehouse_id, route_id, business_date, wave_seq) AS wave_end_utc
FROM wave_numbered;

CREATE TEMPORARY TABLE wave_catalog AS
SELECT DISTINCT
    warehouse_id,
    route_id,
    business_date,
    wave_id,
    wave_start_utc,
    wave_end_utc
FROM wave_loads;

CREATE TEMPORARY TABLE valid_wave_loads AS
SELECT *
FROM wave_loads
WHERE is_valid_order = 1;

CREATE TEMPORARY TABLE wave_sku_exposure AS
SELECT
    w.warehouse_id,
    w.route_id,
    w.business_date,
    w.wave_id,
    sum(dateDiff('minute', greatest(w.wave_start_utc, si.start_at), least(w.wave_end_utc, si.end_at))) AS stockout_exposure_minutes
FROM
(
    SELECT DISTINCT warehouse_id, route_id, business_date, wave_id, wave_start_utc, wave_end_utc, sku_id
    FROM valid_wave_loads
) AS w
INNER JOIN stockout_intervals AS si
    ON si.warehouse_id = w.warehouse_id
    AND si.sku_id = w.sku_id
    AND si.start_at < w.wave_end_utc
    AND si.end_at > w.wave_start_utc
GROUP BY w.warehouse_id, w.route_id, w.business_date, w.wave_id;

INSERT INTO analytics.order_package_audit
SELECT
    wl.order_id,
    wl.package_id,
    wl.warehouse_id,
    wl.route_id,
    wl.business_date,
    wl.wave_id,
    wl.order_final_status,
    wl.loaded_at_utc,
    wl.delivered_at_utc,
    addMinutes(wl.loaded_at_utc, wl.sla_minutes) AS sla_deadline_utc,
    multiIf(
        isNull(wl.delivered_at_utc), 'MISSING_DELIVERY',
        assumeNotNull(wl.delivered_at_utc) > addMinutes(wl.loaded_at_utc, wl.sla_minutes), 'LATE',
        'ON_TIME'
    ) AS sla_status,
    if(countIf(si.warehouse_id != '') > 0, 1, 0) AS stockout_impacted
FROM valid_wave_loads AS wl
LEFT JOIN stockout_intervals AS si
    ON si.warehouse_id = wl.warehouse_id
    AND si.sku_id = wl.sku_id
    AND si.start_at < wl.wave_end_utc
    AND si.end_at > wl.wave_start_utc
GROUP BY
    wl.order_id,
    wl.package_id,
    wl.warehouse_id,
    wl.route_id,
    wl.business_date,
    wl.wave_id,
    wl.order_final_status,
    wl.loaded_at_utc,
    wl.delivered_at_utc,
    wl.sla_minutes;

CREATE TEMPORARY TABLE wave_valid_metrics AS
SELECT
    wl.warehouse_id,
    wl.route_id,
    wl.business_date,
    wl.wave_id,
    count() AS loaded_packages,
    uniqExact(wl.order_id) AS valid_orders,
    countIf(a.sla_status != 'MISSING_DELIVERY') AS delivered_packages,
    countIf(a.sla_status = 'LATE') AS late_packages,
    countIf(a.sla_status = 'MISSING_DELIVERY') AS missing_delivery_packages,
    sum(a.stockout_impacted) AS stockout_impacted_packages
FROM valid_wave_loads AS wl
INNER JOIN analytics.order_package_audit AS a
    ON a.package_id = wl.package_id
    AND a.loaded_at_utc = wl.loaded_at_utc
    AND a.wave_id = wl.wave_id
GROUP BY wl.warehouse_id, wl.route_id, wl.business_date, wl.wave_id;

INSERT INTO analytics.wave_metrics
SELECT
    wc.warehouse_id,
    wc.route_id,
    wc.business_date,
    wc.wave_id,
    wc.wave_start_utc,
    wc.wave_end_utc,
    ifNull(vm.loaded_packages, 0) AS loaded_packages,
    ifNull(vm.valid_orders, 0) AS valid_orders,
    ifNull(vm.delivered_packages, 0) AS delivered_packages,
    ifNull(vm.late_packages, 0) AS late_packages,
    ifNull(vm.missing_delivery_packages, 0) AS missing_delivery_packages,
    ifNull(vm.stockout_impacted_packages, 0) AS stockout_impacted_packages,
    CAST(ifNull(wse.stockout_exposure_minutes, 0) AS Int64) AS stockout_exposure_minutes,
    toDecimal64(if(ifNull(vm.loaded_packages, 0) = 0, 0, round(vm.late_packages / vm.loaded_packages, 4)), 4) AS late_rate,
    multiIf(
        ifNull(vm.loaded_packages, 0) = 0, 'no_valid_orders',
        ifNull(vm.missing_delivery_packages, 0) > 0, 'incomplete',
        ifNull(vm.late_packages, 0) > 0, 'late',
        'complete'
    ) AS wave_status
FROM wave_catalog AS wc
LEFT JOIN wave_valid_metrics AS vm
    ON vm.warehouse_id = wc.warehouse_id
    AND vm.route_id = wc.route_id
    AND vm.business_date = wc.business_date
    AND vm.wave_id = wc.wave_id
LEFT JOIN wave_sku_exposure AS wse
    ON wse.warehouse_id = wc.warehouse_id
    AND wse.route_id = wc.route_id
    AND wse.business_date = wc.business_date
    AND wse.wave_id = wc.wave_id;

INSERT INTO analytics.longest_wave_per_route
SELECT
    warehouse_id,
    route_id,
    business_date,
    wave_id,
    wave_start_utc,
    wave_end_utc,
    loaded_packages,
    valid_orders,
    delivered_packages,
    late_packages,
    missing_delivery_packages,
    stockout_impacted_packages,
    stockout_exposure_minutes,
    late_rate,
    wave_status
FROM
(
    SELECT
        *,
        row_number() OVER (
            PARTITION BY warehouse_id, route_id, business_date
            ORDER BY loaded_packages DESC, wave_start_utc ASC, wave_id ASC
        ) AS rn
    FROM analytics.wave_metrics
)
WHERE rn = 1;

INSERT INTO analytics.data_quality_summary
WITH
    (SELECT count() FROM raw.package_scans) AS n_scan_rows,
    (SELECT count() FROM scans_dedup) AS n_scan_dedup,
    (SELECT count() FROM raw.order_events) AS n_order_rows,
    (SELECT count() FROM final_orders WHERE order_final_status NOT IN ('CANCELLED', 'PAYMENT_FAILED', 'FRAUD_REJECTED')) AS n_valid_orders,
    (SELECT count() FROM analytics.wave_metrics) AS n_waves,
    (SELECT uniqExact(tuple(warehouse_id, route_id)) FROM analytics.wave_metrics) AS n_routes_with_waves,
    (SELECT count() FROM stockout_intervals) AS n_stockout_intervals
SELECT concat(
    '{',
    '"n_package_scan_rows_loaded":', toString(n_scan_rows), ',',
    '"n_package_scan_rows_after_dedup":', toString(n_scan_dedup), ',',
    '"n_order_event_rows_loaded":', toString(n_order_rows), ',',
    '"n_valid_orders":', toString(n_valid_orders), ',',
    '"n_waves":', toString(n_waves), ',',
    '"n_routes_with_waves":', toString(n_routes_with_waves), ',',
    '"n_stockout_intervals":', toString(n_stockout_intervals), ',',
    '"timezone_handling":"warehouse local business dates via typed toTimeZone dispatch",',
    '"deduplication_rules":"scan_id latest ingested_at; order argMax by event_time,event_version,ingested_at",',
    '"notes":"delivery waves are sessionized in ClickHouse with 20 minute event-time gaps"',
    '}'
);
SQL

bash /app/workspace/run.sh --output /app/answer
