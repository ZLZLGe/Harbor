---
name: bigquery-analyst
description: "Expert BigQuery data analysis using MCP tools. Perform schema discovery, data profiling, distribution analysis, anomaly detection, time series exploration, data quality assessment, and ad-hoc analytical queries against any BigQuery dataset. Use when the user asks to analyze, explore, profile, investigate, or query data in BigQuery, or asks questions that can be answered by querying a BigQuery dataset (e.g., 'how many users signed up last week?', 'show me the distribution of order values', 'find anomalies in the revenue data', 'what does the customers table look like?')."
---

# BigQuery Analyst

Expert analysis workflow for any BigQuery dataset using MCP tools.

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `mcp__bigquery__list_dataset_ids` | List all datasets in a project |
| `mcp__bigquery__list_table_ids` | List tables/views in a dataset |
| `mcp__bigquery__get_dataset_info` | Get dataset metadata |
| `mcp__bigquery__get_table_info` | Get table schema, row count, size |
| `mcp__bigquery__execute_sql` | Run SQL queries (read-only preferred) |
| `mcp__bigquery__search_catalog` | Search Data Catalog for tables by keyword |
| `mcp__bigquery__ask_data_insights` | AI-driven insights on a table |
| `mcp__bigquery__forecast` | Time series forecasting |
| `mcp__bigquery__analyze_contribution` | Contribution/driver analysis |

## Analysis Workflow

Follow this sequence, skipping steps when the user's intent is clear:

### 1. Orient

Discover what data exists. If the user specifies a table, skip to step 2.

- `list_dataset_ids` to find datasets
- `list_table_ids` on relevant datasets
- `search_catalog` if looking for a topic (e.g., "revenue", "users")

### 2. Understand Schema

Before writing any query, get the schema first:

- `get_table_info` on target tables — note column names, types, partitioning, row count
- Identify: primary keys, timestamps, categorical vs numeric columns, partition/cluster columns

### 3. Profile

Run targeted profiling queries to understand the data shape. See `references/analysis-patterns.md` section "Data Profiling" for templates. Key checks:

- Row count and distinct count on key columns
- Null rates on important columns
- Value distributions on categorical columns (top-N)
- Min/max/mean/stddev on numeric columns
- Date range on timestamp columns

### 4. Analyze

Execute the analysis matching the user's question. Use `references/analysis-patterns.md` for SQL templates:

| User intent | Pattern to use |
|---|---|
| "What does X look like?" | Data Profiling, Distribution Analysis |
| "Find outliers / anomalies" | Anomaly Detection (z-score or IQR) |
| "Show me the trend" | Time Series Exploration |
| "Compare periods" | Period-over-Period Comparison |
| "Are there data quality issues?" | Data Quality Assessment |
| "How does X relate to Y?" | Correlation, Segmented Analysis |
| "What drives X?" | `analyze_contribution` tool, Segmented Analysis |
| "Predict / forecast X" | `forecast` tool |
| General questions about the data | `ask_data_insights` tool, then targeted SQL |

### 5. Present

- Lead with the answer to the user's question in plain language
- Support with key numbers and comparisons
- Note caveats: sample size, null rates, date range of data
- Suggest follow-up analyses when patterns are interesting

## Query Guidelines

- Always use fully qualified table names: `project.dataset.table`
- Use `LIMIT` on exploratory queries (start with 1000, adjust as needed)
- Prefer `APPROX_QUANTILES` and `APPROX_COUNT_DISTINCT` for large tables
- Use partition filters when available to reduce scan cost
- Use `SAFE_DIVIDE` to avoid division-by-zero errors
- Format numbers for readability: `ROUND()`, `FORMAT()` as appropriate
- When column names or structure are uncertain, run a `SELECT * LIMIT 5` first

## SQL Reference

Reusable SQL templates for all analysis types are in [references/analysis-patterns.md](references/analysis-patterns.md). Consult this file for:

- **Data Profiling** — column stats, null rates, cardinality, top-N values
- **Distribution Analysis** — percentiles, histograms, bucket analysis
- **Anomaly Detection** — z-score outliers, IQR method, day-over-day spikes
- **Time Series** — trends, moving averages, seasonality, gap detection
- **Join Discovery** — foreign key candidates, join coverage checks
- **Data Quality** — duplicates, orphan records, format validation, freshness
- **Advanced** — correlation, segmentation, cumulative distribution, cohort retention
