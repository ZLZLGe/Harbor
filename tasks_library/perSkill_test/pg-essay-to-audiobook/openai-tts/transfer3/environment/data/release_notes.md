# Product Release 2026.03

## Reliability Improvements
The scheduler now retries lease acquisition with bounded jitter and stores lease state snapshots every fifteen seconds. This reduces coordinated retry storms during rolling restarts.

## Search Relevance Update
Ranking now blends lexical score with session-level recency and enforces diversity across duplicated vendors. Result pages should feel less repetitive for broad product queries.

## Billing Controls
Invoice generation now validates tax jurisdiction mapping before posting ledgers. Accounts with invalid mappings are paused and surfaced through a dedicated audit queue.

## Observability Additions
Alert streams now include correlation ids for worker retries and queue lag events. Dashboards include a new panel summarizing p95 backlog age by region.
