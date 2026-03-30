#!/bin/bash

set -euo pipefail

mkdir -p /workspace/answer

cat > /workspace/answer/worker_queue_patch.sql <<'SQL'
BEGIN;

DROP POLICY IF EXISTS queue_jobs_tenant_access ON queue_jobs;

ALTER TABLE queue_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE queue_jobs FORCE ROW LEVEL SECURITY;

CREATE POLICY queue_jobs_tenant_access
ON queue_jobs
FOR ALL
TO queue_worker
USING (tenant_slug = (SELECT current_setting('app.current_tenant_id', true)))
WITH CHECK (tenant_slug = (SELECT current_setting('app.current_tenant_id', true)));

DROP INDEX IF EXISTS queue_jobs_ready_claim_idx;
CREATE INDEX queue_jobs_ready_claim_idx
ON queue_jobs (tenant_slug, priority DESC, run_at ASC, id ASC)
WHERE status = 'pending';

DROP INDEX IF EXISTS queue_jobs_pending_backlog_idx;
CREATE INDEX queue_jobs_pending_backlog_idx
ON queue_jobs (tenant_slug, queue_name)
INCLUDE (run_at)
WHERE status = 'pending';

CREATE OR REPLACE FUNCTION claim_next_job(p_worker_name text)
RETURNS TABLE (
  job_id bigint,
  tenant_slug text,
  queue_name text,
  priority integer,
  run_at timestamptz,
  payload jsonb
)
LANGUAGE sql
SECURITY INVOKER
AS $$
  WITH next_job AS (
    SELECT q.id
    FROM queue_jobs AS q
    WHERE q.status = 'pending'
      AND q.run_at <= now()
    ORDER BY q.priority DESC, q.run_at ASC, q.id ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
  ),
  claimed AS (
    UPDATE queue_jobs AS q
    SET status = 'processing',
        locked_by = p_worker_name,
        locked_at = clock_timestamp(),
        started_at = clock_timestamp(),
        attempts = q.attempts + 1
    FROM next_job
    WHERE q.id = next_job.id
    RETURNING q.id, q.tenant_slug, q.queue_name, q.priority, q.run_at, q.payload
  )
  SELECT
    claimed.id,
    claimed.tenant_slug,
    claimed.queue_name,
    claimed.priority,
    claimed.run_at,
    claimed.payload
  FROM claimed;
$$;

COMMIT;
SQL
