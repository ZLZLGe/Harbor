# Task

A seeded Postgres helpdesk database is available inside the container. The dashboard workload lives in:

- `/workspace/environment/workload/agent_load.sql`
- `/workspace/environment/workload/enterprise_backlog.sql`
- `/workspace/environment/workload/latest_customer_reply.sql`
- `/workspace/environment/workload/reply_lookup_diagnostic.sql`

The current schema already contains the workload views, but one of them is intentionally written in a slow way and the large tables do not have the indexes that the dashboard needs.

Write `answer/support_dashboard_fix.sql`.

The verifier will apply your SQL file to a freshly seeded database and then check both correctness and query plans.

## What You Can Use

Start the bundled local Postgres server and reset the database with:

```bash
/workspace/environment/bin/start-postgres.sh
export PGHOST=/tmp/support-dashboard-pg
export PGPORT=55432
export PGUSER=postgres
/workspace/environment/bin/reset-support-db.sh
```

Then inspect the seeded objects, run the workload queries, and use `EXPLAIN (ANALYZE, BUFFERS)` while iterating.

## Requirements

- Your output must be a single SQL file at `answer/support_dashboard_fix.sql`.
- Applying that file with `psql -v ON_ERROR_STOP=1 -d support_dashboard -f answer/support_dashboard_fix.sql` must succeed on a freshly seeded database.
- Keep the result sets of `agent_load.sql`, `enterprise_backlog.sql`, and `latest_customer_reply.sql` exactly unchanged.
- Replace `dashboard_latest_customer_reply` with a semantically equivalent normal view that is faster on this dataset.
- Add only the indexes you need so the dashboard workload avoids sequential scans on `tickets` and `ticket_events`.
- The diagnostic lookup in `reply_lookup_diagnostic.sql` must use an index-only scan and report `Heap Fetches: 0` under `EXPLAIN (ANALYZE, BUFFERS)`.
- Do not change table data, table names, or planner settings.

## Notes

- The seeded database is deterministic. If your SQL is correct, the verifier will rebuild the database from scratch and reproduce the same plan checks every time.
- You do not need to edit anything under `/workspace/environment/`.
