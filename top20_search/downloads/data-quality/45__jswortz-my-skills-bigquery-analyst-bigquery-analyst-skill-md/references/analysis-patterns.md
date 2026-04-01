# BigQuery Analysis Patterns

## Table of Contents

1. [Data Profiling](#data-profiling)
2. [Distribution Analysis](#distribution-analysis)
3. [Anomaly Detection](#anomaly-detection)
4. [Time Series Exploration](#time-series-exploration)
5. [Join & Relationship Discovery](#join--relationship-discovery)
6. [Data Quality Assessment](#data-quality-assessment)
7. [Advanced Analytical Patterns](#advanced-analytical-patterns)

---

## Data Profiling

### Column-Level Statistics

```sql
-- Numeric column profiling
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT {col}) AS distinct_values,
  COUNTIF({col} IS NULL) AS null_count,
  ROUND(COUNTIF({col} IS NULL) / COUNT(*) * 100, 2) AS null_pct,
  MIN({col}) AS min_val,
  MAX({col}) AS max_val,
  ROUND(AVG({col}), 4) AS mean_val,
  ROUND(STDDEV({col}), 4) AS stddev_val
FROM `{table}`
```

### String Column Profiling

```sql
SELECT
  COUNT(DISTINCT {col}) AS distinct_values,
  COUNTIF({col} IS NULL) AS null_count,
  MIN(LENGTH({col})) AS min_length,
  MAX(LENGTH({col})) AS max_length,
  ROUND(AVG(LENGTH({col})), 1) AS avg_length
FROM `{table}`
```

### Quick Full-Table Profile

```sql
-- Row count and byte size
SELECT
  COUNT(*) AS row_count,
  COUNT(*) - COUNT(DISTINCT {pk_col}) AS duplicate_count
FROM `{table}`
```

### Top-N Values for Categorical Columns

```sql
SELECT {col}, COUNT(*) AS freq,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2) AS pct
FROM `{table}`
WHERE {col} IS NOT NULL
GROUP BY {col}
ORDER BY freq DESC
LIMIT 20
```

---

## Distribution Analysis

### Percentile Distribution

```sql
SELECT
  APPROX_QUANTILES({col}, 100)[OFFSET(5)] AS p5,
  APPROX_QUANTILES({col}, 100)[OFFSET(25)] AS p25,
  APPROX_QUANTILES({col}, 100)[OFFSET(50)] AS median,
  APPROX_QUANTILES({col}, 100)[OFFSET(75)] AS p75,
  APPROX_QUANTILES({col}, 100)[OFFSET(95)] AS p95,
  APPROX_QUANTILES({col}, 100)[OFFSET(99)] AS p99
FROM `{table}`
```

### Histogram Buckets

```sql
SELECT
  bucket,
  COUNT(*) AS freq,
  REPEAT('*', CAST(COUNT(*) * 50.0 / MAX(COUNT(*)) OVER() AS INT64)) AS bar
FROM (
  SELECT ML.BUCKETIZE({col}, [{lower}, {mid1}, {mid2}, {upper}]) AS bucket
  FROM `{table}`
)
GROUP BY bucket
ORDER BY bucket
```

### Automatic Equal-Width Histogram

```sql
WITH stats AS (
  SELECT MIN({col}) AS lo, MAX({col}) AS hi FROM `{table}`
),
bucketed AS (
  SELECT FLOOR(({col} - lo) / NULLIF((hi - lo) / 20, 0)) AS bin
  FROM `{table}`, stats
  WHERE {col} IS NOT NULL
)
SELECT bin, COUNT(*) AS freq
FROM bucketed
GROUP BY bin
ORDER BY bin
```

---

## Anomaly Detection

### Z-Score Outliers

```sql
WITH stats AS (
  SELECT AVG({col}) AS mu, STDDEV({col}) AS sigma
  FROM `{table}`
)
SELECT *, ROUND(({col} - mu) / NULLIF(sigma, 0), 2) AS z_score
FROM `{table}`, stats
WHERE ABS(({col} - mu) / NULLIF(sigma, 0)) > 3
ORDER BY z_score DESC
```

### IQR-Based Outliers

```sql
WITH quartiles AS (
  SELECT
    APPROX_QUANTILES({col}, 4)[OFFSET(1)] AS q1,
    APPROX_QUANTILES({col}, 4)[OFFSET(3)] AS q3
  FROM `{table}`
),
bounds AS (
  SELECT q1, q3, q3 - q1 AS iqr,
    q1 - 1.5 * (q3 - q1) AS lower_bound,
    q3 + 1.5 * (q3 - q1) AS upper_bound
  FROM quartiles
)
SELECT t.*
FROM `{table}` t, bounds
WHERE t.{col} < lower_bound OR t.{col} > upper_bound
```

### Day-over-Day Change Detection

```sql
WITH daily AS (
  SELECT DATE({ts_col}) AS dt, {agg_func}({metric_col}) AS val
  FROM `{table}`
  GROUP BY dt
),
changes AS (
  SELECT *, val - LAG(val) OVER (ORDER BY dt) AS delta,
    SAFE_DIVIDE(val - LAG(val) OVER (ORDER BY dt), LAG(val) OVER (ORDER BY dt)) AS pct_change
  FROM daily
)
SELECT * FROM changes
WHERE ABS(pct_change) > 0.5  -- >50% change
ORDER BY dt DESC
```

---

## Time Series Exploration

### Trend with Moving Average

```sql
SELECT
  DATE({ts_col}) AS dt,
  {agg_func}({metric_col}) AS daily_val,
  AVG({agg_func}({metric_col})) OVER (
    ORDER BY DATE({ts_col})
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS ma_7d
FROM `{table}`
GROUP BY dt
ORDER BY dt
```

### Day-of-Week Seasonality

```sql
SELECT
  FORMAT_DATE('%A', DATE({ts_col})) AS day_name,
  EXTRACT(DAYOFWEEK FROM DATE({ts_col})) AS dow,
  {agg_func}({metric_col}) AS val,
  COUNT(*) AS n
FROM `{table}`
GROUP BY day_name, dow
ORDER BY dow
```

### Period-over-Period Comparison

```sql
WITH current_period AS (
  SELECT {agg_func}({metric_col}) AS val
  FROM `{table}`
  WHERE DATE({ts_col}) BETWEEN '{start}' AND '{end}'
),
prior_period AS (
  SELECT {agg_func}({metric_col}) AS val
  FROM `{table}`
  WHERE DATE({ts_col}) BETWEEN DATE_SUB('{start}', INTERVAL {period_days} DAY)
    AND DATE_SUB('{end}', INTERVAL {period_days} DAY)
)
SELECT
  c.val AS current_val,
  p.val AS prior_val,
  ROUND(SAFE_DIVIDE(c.val - p.val, p.val) * 100, 2) AS pct_change
FROM current_period c, prior_period p
```

### Gap Detection (Missing Dates)

```sql
WITH date_spine AS (
  SELECT d FROM UNNEST(
    GENERATE_DATE_ARRAY(
      (SELECT MIN(DATE({ts_col})) FROM `{table}`),
      (SELECT MAX(DATE({ts_col})) FROM `{table}`)
    )
  ) AS d
),
actual AS (
  SELECT DISTINCT DATE({ts_col}) AS dt FROM `{table}`
)
SELECT d AS missing_date
FROM date_spine
LEFT JOIN actual ON d = dt
WHERE dt IS NULL
ORDER BY d
```

---

## Join & Relationship Discovery

### Candidate Foreign Keys (Cardinality Match)

```sql
-- Run separately for each table pair to find join candidates
SELECT
  '{table_a}.{col_a}' AS source,
  '{table_b}.{col_b}' AS target,
  (SELECT COUNT(DISTINCT {col_a}) FROM `{table_a}`) AS source_distinct,
  (SELECT COUNT(DISTINCT {col_b}) FROM `{table_b}`) AS target_distinct
```

### Join Coverage Check

```sql
SELECT
  COUNT(*) AS total_left,
  COUNTIF(r.{join_col} IS NOT NULL) AS matched,
  COUNTIF(r.{join_col} IS NULL) AS unmatched,
  ROUND(COUNTIF(r.{join_col} IS NOT NULL) / COUNT(*) * 100, 2) AS match_pct
FROM `{left_table}` l
LEFT JOIN `{right_table}` r USING ({join_col})
```

---

## Data Quality Assessment

### Duplicate Detection

```sql
SELECT {cols}, COUNT(*) AS dup_count
FROM `{table}`
GROUP BY {cols}
HAVING COUNT(*) > 1
ORDER BY dup_count DESC
LIMIT 100
```

### Referential Integrity Check

```sql
SELECT l.{fk_col}, COUNT(*) AS orphan_count
FROM `{child_table}` l
LEFT JOIN `{parent_table}` r ON l.{fk_col} = r.{pk_col}
WHERE r.{pk_col} IS NULL AND l.{fk_col} IS NOT NULL
GROUP BY l.{fk_col}
ORDER BY orphan_count DESC
```

### Format Validation (Regex)

```sql
SELECT {col}, COUNT(*) AS bad_count
FROM `{table}`
WHERE NOT REGEXP_CONTAINS(CAST({col} AS STRING), r'{pattern}')
  AND {col} IS NOT NULL
GROUP BY {col}
ORDER BY bad_count DESC
LIMIT 50
```

### Freshness Check

```sql
SELECT
  MAX({ts_col}) AS latest_record,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX({ts_col}), HOUR) AS hours_stale
FROM `{table}`
```

---

## Advanced Analytical Patterns

### Correlation Between Two Numeric Columns

```sql
SELECT ROUND(CORR({col_a}, {col_b}), 4) AS pearson_r
FROM `{table}`
WHERE {col_a} IS NOT NULL AND {col_b} IS NOT NULL
```

### Segmented Analysis

```sql
SELECT
  {segment_col},
  COUNT(*) AS n,
  ROUND(AVG({metric_col}), 2) AS avg_val,
  ROUND(STDDEV({metric_col}), 2) AS std_val,
  APPROX_QUANTILES({metric_col}, 4)[OFFSET(2)] AS median_val
FROM `{table}`
GROUP BY {segment_col}
ORDER BY n DESC
```

### Cumulative Distribution

```sql
SELECT
  {col},
  CUME_DIST() OVER (ORDER BY {col}) AS cumulative_pct,
  PERCENT_RANK() OVER (ORDER BY {col}) AS percent_rank
FROM `{table}`
```

### Cohort Retention (Generic)

```sql
WITH first_action AS (
  SELECT {user_col}, MIN(DATE({ts_col})) AS cohort_date
  FROM `{table}`
  GROUP BY {user_col}
),
activity AS (
  SELECT {user_col}, DATE({ts_col}) AS activity_date
  FROM `{table}`
)
SELECT
  f.cohort_date,
  DATE_DIFF(a.activity_date, f.cohort_date, DAY) AS days_since,
  COUNT(DISTINCT a.{user_col}) AS active_users
FROM first_action f
JOIN activity a USING ({user_col})
GROUP BY cohort_date, days_since
ORDER BY cohort_date, days_since
```
