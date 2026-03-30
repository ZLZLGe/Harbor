# Task

A seeded Postgres background-job database is available inside the container. It already contains a `queue_jobs` table, a `claim_next_job(text)` function, and a worker role named `queue_worker`, but the current implementation is intentionally wrong:

- the claim path blocks under contention,
- tenant isolation is not enforced at the database layer,
- and the queue probes fall back to sequential scans on `queue_jobs`.

Write `answer/worker_queue_patch.sql`.

The verifier will reset the database, apply your SQL file to a fresh seed, and then run concurrent claim, row-level security, and plan checks.

## What You Can Use

Start the bundled local Postgres server and reset the database with:

```bash
/workspace/environment/bin/start-postgres.sh
export PGHOST=/tmp/worker-queue-pg
export PGPORT=55433
export PGUSER=postgres
/workspace/environment/bin/reset-worker-queue-db.sh
```

Useful probe queries are available at:

- `/workspace/environment/probes/ready_claim_probe.sql`
- `/workspace/environment/probes/tenant_backlog_probe.sql`

To inspect row-level security behavior, connect as the seeded worker role and set the tenant context before running the probes:

```sql
\c worker_queue queue_worker
SET app.current_tenant_id = 'tenant_alpha';
```

## Requirements

- Your output must be a single SQL file at `answer/worker_queue_patch.sql`.
- Applying that file with `psql -v ON_ERROR_STOP=1 -d worker_queue -f answer/worker_queue_patch.sql` must succeed on a freshly seeded database.
- Do not modify the seeded table data when your patch is applied.
- Replace `claim_next_job(worker_name text)` so it atomically claims at most one due `pending` job for the current tenant, updates it to `processing`, sets `locked_by`, `locked_at`, and `started_at`, increments `attempts`, and returns zero rows when nothing is available.
- The claim ordering must stay `priority DESC, run_at ASC, id ASC`.
- Use `FOR UPDATE SKIP LOCKED` in the claim path so two open transactions for the same tenant can claim different jobs without waiting on the same row.
- Enable and force row-level security on `queue_jobs`.
- When `queue_worker` sets `app.current_tenant_id`, it must only be able to read and update rows for that tenant.
- Add only the indexes you need so `ready_claim_probe.sql` and `tenant_backlog_probe.sql`, run as `queue_worker` with a tenant context, avoid sequential scans on `queue_jobs`.
- Do not change table names, role names, or planner settings.

## Notes

- The seeded database is deterministic. If your patch is correct, the verifier will rebuild the database from scratch and reproduce the same checks every time.
- You do not need to edit anything under `/workspace/environment/`.
