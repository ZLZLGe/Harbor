#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/workspace/data}"
SQL_DIR="${SQL_DIR:-/app/workspace/sql}"
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-127.0.0.1}"
OUTPUT_DIR="/app/answer"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

start_clickhouse() {
  if clickhouse-client --host "$CLICKHOUSE_HOST" --query "SELECT 1" >/dev/null 2>&1; then
    return
  fi

  mkdir -p /var/lib/clickhouse /var/log/clickhouse-server /tmp/clickhouse-wave
  clickhouse-server --config-file=/etc/clickhouse-server/config.xml >/tmp/clickhouse-wave/server.log 2>&1 &

  for _ in $(seq 1 100); do
    if clickhouse-client --host "$CLICKHOUSE_HOST" --query "SELECT 1" >/dev/null 2>&1; then
      return
    fi
    sleep 0.5
  done

  tail -200 /tmp/clickhouse-wave/server.log >&2 || true
  echo "ClickHouse did not become ready" >&2
  exit 1
}

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required input file: $1" >&2
    exit 1
  fi
}

start_clickhouse

require_file "$DATA_DIR/package_scans/scans.csv.gz"
require_file "$DATA_DIR/order_events/events.jsonl.gz"
require_file "$DATA_DIR/inventory_snapshots/snapshots.csv.gz"
require_file "$DATA_DIR/reference/warehouses.csv"
require_file "$DATA_DIR/reference/route_sla.csv"
require_file "$DATA_DIR/reference/skus.csv"

clickhouse-client --host "$CLICKHOUSE_HOST" --multiquery <<'SQL'
DROP DATABASE IF EXISTS raw;
DROP DATABASE IF EXISTS analytics;
CREATE DATABASE raw;
CREATE DATABASE analytics;

CREATE TABLE raw.package_scans (
    scan_id String,
    package_id String,
    order_id String,
    warehouse_id String,
    route_id String,
    sku_id String,
    scan_type LowCardinality(String),
    event_time DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC')
) ENGINE = MergeTree()
ORDER BY (warehouse_id, route_id, package_id, scan_type, event_time, ingested_at);

CREATE TABLE raw.order_events (
    order_id String,
    status LowCardinality(String),
    event_time DateTime64(3, 'UTC'),
    event_version UInt32,
    ingested_at DateTime64(3, 'UTC')
) ENGINE = MergeTree()
ORDER BY (order_id, event_time, event_version, ingested_at);

CREATE TABLE raw.inventory_snapshots (
    snapshot_id String,
    warehouse_id String,
    sku_id String,
    available_to_promise Int32,
    event_time DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC')
) ENGINE = MergeTree()
ORDER BY (warehouse_id, sku_id, event_time, ingested_at, snapshot_id);

CREATE TABLE raw.warehouses (
    warehouse_id String,
    region LowCardinality(String),
    timezone String
) ENGINE = MergeTree()
ORDER BY warehouse_id;

CREATE TABLE raw.route_sla (
    warehouse_id String,
    route_id String,
    sla_minutes UInt32
) ENGINE = MergeTree()
ORDER BY (warehouse_id, route_id);

CREATE TABLE raw.skus (
    sku_id String,
    product_family LowCardinality(String),
    active UInt8
) ENGINE = MergeTree()
ORDER BY sku_id;
SQL

gzip -dc "$DATA_DIR/package_scans/scans.csv.gz" | clickhouse-client --host "$CLICKHOUSE_HOST" --query "INSERT INTO raw.package_scans FORMAT CSVWithNames"
gzip -dc "$DATA_DIR/order_events/events.jsonl.gz" | clickhouse-client --host "$CLICKHOUSE_HOST" --query "INSERT INTO raw.order_events FORMAT JSONEachRow"
gzip -dc "$DATA_DIR/inventory_snapshots/snapshots.csv.gz" | clickhouse-client --host "$CLICKHOUSE_HOST" --query "INSERT INTO raw.inventory_snapshots FORMAT CSVWithNames"
clickhouse-client --host "$CLICKHOUSE_HOST" --query "INSERT INTO raw.warehouses FORMAT CSVWithNames" < "$DATA_DIR/reference/warehouses.csv"
clickhouse-client --host "$CLICKHOUSE_HOST" --query "INSERT INTO raw.route_sla FORMAT CSVWithNames" < "$DATA_DIR/reference/route_sla.csv"
clickhouse-client --host "$CLICKHOUSE_HOST" --query "INSERT INTO raw.skus FORMAT CSVWithNames" < "$DATA_DIR/reference/skus.csv"

clickhouse-client --host "$CLICKHOUSE_HOST" --multiquery < "$SQL_DIR/build_waves.sql"

mkdir -p "$OUTPUT_DIR"
clickhouse-client --host "$CLICKHOUSE_HOST" --query "
SELECT
    warehouse_id,
    route_id,
    toString(business_date) AS business_date,
    wave_id,
    formatDateTime(wave_start_utc, '%F %T') AS wave_start_utc,
    formatDateTime(wave_end_utc, '%F %T') AS wave_end_utc,
    loaded_packages,
    valid_orders,
    delivered_packages,
    late_packages,
    missing_delivery_packages,
    stockout_impacted_packages,
    stockout_exposure_minutes,
    toString(late_rate) AS late_rate,
    wave_status
FROM analytics.wave_metrics
ORDER BY warehouse_id, route_id, business_date, wave_start_utc, wave_id
FORMAT CSVWithNames" > "$OUTPUT_DIR/wave_metrics.csv"

clickhouse-client --host "$CLICKHOUSE_HOST" --query "
SELECT
    warehouse_id,
    route_id,
    toString(business_date) AS business_date,
    wave_id,
    loaded_packages,
    dateDiff('minute', wave_start_utc, wave_end_utc) AS wave_duration_minutes,
    toString(late_rate) AS late_rate,
    stockout_exposure_minutes
FROM analytics.longest_wave_per_route
ORDER BY warehouse_id, route_id, business_date
FORMAT CSVWithNames" > "$OUTPUT_DIR/longest_wave_per_route.csv"

clickhouse-client --host "$CLICKHOUSE_HOST" --query "
SELECT
    order_id,
    package_id,
    warehouse_id,
    route_id,
    toString(business_date) AS business_date,
    wave_id,
    order_final_status,
    formatDateTime(loaded_at_utc, '%F %T') AS loaded_at_utc,
    if(isNull(delivered_at_utc), '', formatDateTime(assumeNotNull(delivered_at_utc), '%F %T')) AS delivered_at_utc,
    formatDateTime(sla_deadline_utc, '%F %T') AS sla_deadline_utc,
    sla_status,
    stockout_impacted
FROM analytics.order_package_audit
ORDER BY warehouse_id, route_id, business_date, wave_id, loaded_at_utc, package_id
FORMAT TSVWithNames" > "$OUTPUT_DIR/order_package_audit.tsv"

clickhouse-client --host "$CLICKHOUSE_HOST" --query "SELECT payload FROM analytics.data_quality_summary LIMIT 1 FORMAT TabSeparatedRaw" > "$OUTPUT_DIR/data_quality_summary.json"
