senior-data-engineer reference

Troubleshooting

Pipeline Failures

Symptom: Airflow DAG fails with timeout

Task exceeded max execution time

Solution:

Check resource allocation

Profile slow operations

Add incremental processing

# Increase timeout
default_args = {
'execution_timeout': timedelta(hours=2),
}

# Or use incremental loads
WHERE updated_at > '{{ prev_ds }}'

Symptom: Spark job OOM

java.lang.OutOfMemoryError: Java heap space

Solution:

Increase executor memory

Reduce partition size

Use disk spill

spark.conf.set("spark.executor.memory", "8g")
spark.conf.set("spark.sql.shuffle.partitions", "200")
spark.conf.set("spark.memory.fraction", "0.8")

Symptom: Kafka consumer lag increasing

Consumer lag: 1000000 messages

Solution:

Increase consumer parallelism

Optimize processing logic

Scale consumer group

# Add more partitions
kafka-topics.sh --alter \
--bootstrap-server localhost:9092 \
--topic user-events \
--partitions 24

Data Quality Issues

Symptom: Duplicate records appearing

Expected unique, found 150 duplicates

Solution:

Add deduplication logic

Use merge/upsert operations

-- dbt incremental with dedup
{{
config(
materialized='incremental',
unique_key='order_id'
)
}}

SELECT * FROM (
SELECT
*,
ROW_NUMBER() OVER (
PARTITION BY order_id
ORDER BY updated_at DESC
) as rn
FROM {{ source('raw', 'orders') }}
) WHERE rn = 1

Symptom: Stale data in tables

Last update: 3 days ago

Solution:

Check upstream pipeline status

Verify source availability

Add freshness monitoring

# dbt freshness check
sources:
- name: "raw"
freshness:
warn_after: {count: 12, period: hour}
error_after: {count: 24, period: hour}
loaded_at_field: _loaded_at

Symptom: Schema drift detected

Column 'new_field' not in expected schema

Solution:

Update data contract

Modify transformations

Communicate with producers

# Handle schema evolution
df = spark.read.format("delta") \
.option("mergeSchema", "true") \
.load("/data/orders")

Performance Issues

Symptom: Query takes hours

Query runtime: 4 hours (expected: 30 minutes)

Solution:

Check query plan

Add proper partitioning

Optimize joins

-- Before: Full table scan
SELECT * FROM orders WHERE order_date = '2024-01-15';

-- After: Partition pruning
-- Table partitioned by order_date
SELECT * FROM orders WHERE order_date = '2024-01-15';

-- Add clustering for frequent filters
ALTER TABLE orders CLUSTER BY (customer_id);

Symptom: dbt model takes too long

Model fct_orders completed in 45 minutes

Solution:

Use incremental materialization

Reduce upstream dependencies

Pre-aggregate where possible

-- Convert to incremental
{{
config(
materialized='incremental',
unique_key='order_id',
on_schema_change='sync_all_columns'
)
}}

SELECT * FROM {{ ref('stg_orders') }}
{% if is_incremental() %}
WHERE _loaded_at > (SELECT MAX(_loaded_at) FROM {{ this }})
{% endif %}