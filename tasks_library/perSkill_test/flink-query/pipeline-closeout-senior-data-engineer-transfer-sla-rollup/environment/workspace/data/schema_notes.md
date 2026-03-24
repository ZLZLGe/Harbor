# Pipeline Closeout SLA Dataset

This dataset models a bounded pipeline-operations stream.

## `pipeline_task_lifecycle.csv.gz`

CSV columns:

1. `event_time_utc`: ISO-8601 UTC timestamp
2. `pipeline_id`: pipeline identifier
3. `task_id`: task identifier within the pipeline
4. `event_type`: one of `BLOCKED`, `READY`, `FAILED`, or other lifecycle labels
5. `owner_team`: extra context, not required for the rollup

Only `BLOCKED`, `READY`, and `FAILED` affect the required output. Other lifecycle labels may be ignored.

## `pipeline_close_events.csv.gz`

CSV columns:

1. `close_time_utc`: ISO-8601 UTC timestamp
2. `pipeline_id`: pipeline identifier
3. `close_reason`: informational field, not required for the rollup

Exactly one summary line should be emitted for each pipeline that has a close event.
