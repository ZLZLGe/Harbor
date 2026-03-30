\set ON_ERROR_STOP on

SET client_min_messages = warning;
SET timezone = 'UTC';

DROP FUNCTION IF EXISTS claim_next_job(text);
DROP TABLE IF EXISTS queue_jobs;
DROP TABLE IF EXISTS queue_tenants;

CREATE TABLE queue_tenants (
  tenant_slug text PRIMARY KEY,
  display_name text NOT NULL,
  tier text NOT NULL
);

CREATE TABLE queue_jobs (
  id bigint PRIMARY KEY,
  tenant_slug text NOT NULL REFERENCES queue_tenants(tenant_slug),
  queue_name text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  priority integer NOT NULL CHECK (priority BETWEEN 0 AND 100),
  attempts integer NOT NULL DEFAULT 0,
  run_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL,
  locked_by text,
  locked_at timestamptz,
  started_at timestamptz,
  completed_at timestamptz,
  last_error text
);

GRANT USAGE ON SCHEMA public TO queue_worker;
GRANT SELECT, UPDATE ON queue_jobs TO queue_worker;

INSERT INTO queue_tenants (tenant_slug, display_name, tier) VALUES
  ('tenant_alpha', 'Tenant Alpha', 'enterprise'),
  ('tenant_beta', 'Tenant Beta', 'enterprise'),
  ('tenant_gamma', 'Tenant Gamma', 'growth'),
  ('tenant_delta', 'Tenant Delta', 'growth');

INSERT INTO queue_jobs (
  id,
  tenant_slug,
  queue_name,
  payload,
  status,
  priority,
  attempts,
  run_at,
  created_at,
  locked_by,
  locked_at,
  started_at,
  completed_at,
  last_error
) VALUES
  (
    1,
    'tenant_alpha',
    'email',
    jsonb_build_object('kind', 'special', 'job', 1),
    'pending',
    100,
    0,
    timestamptz '2026-01-01 08:00:00+00',
    timestamptz '2025-12-31 23:55:00+00',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
  ),
  (
    2,
    'tenant_alpha',
    'email',
    jsonb_build_object('kind', 'special', 'job', 2),
    'pending',
    95,
    1,
    timestamptz '2026-01-01 08:05:00+00',
    timestamptz '2025-12-31 23:57:00+00',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
  ),
  (
    3,
    'tenant_beta',
    'billing',
    jsonb_build_object('kind', 'special', 'job', 3),
    'pending',
    99,
    0,
    timestamptz '2026-01-01 08:02:00+00',
    timestamptz '2025-12-31 23:56:00+00',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
  ),
  (
    4,
    'tenant_beta',
    'billing',
    jsonb_build_object('kind', 'special', 'job', 4),
    'pending',
    94,
    0,
    timestamptz '2026-01-01 08:07:00+00',
    timestamptz '2025-12-31 23:58:00+00',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
  ),
  (
    5,
    'tenant_gamma',
    'webhook',
    jsonb_build_object('kind', 'special', 'job', 5),
    'pending',
    93,
    0,
    timestamptz '2026-01-01 08:08:00+00',
    timestamptz '2026-01-01 00:01:00+00',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
  ),
  (
    6,
    'tenant_delta',
    'email',
    jsonb_build_object('kind', 'special', 'job', 6),
    'processing',
    88,
    2,
    timestamptz '2026-01-01 09:00:00+00',
    timestamptz '2026-01-01 00:02:00+00',
    'existing-worker',
    timestamptz '2026-01-01 09:00:10+00',
    timestamptz '2026-01-01 09:00:10+00',
    NULL,
    NULL
  ),
  (
    7,
    'tenant_alpha',
    'reports',
    jsonb_build_object('kind', 'special', 'job', 7),
    'completed',
    40,
    1,
    timestamptz '2025-12-30 12:00:00+00',
    timestamptz '2025-12-30 11:30:00+00',
    'worker-finished',
    timestamptz '2025-12-30 12:00:05+00',
    timestamptz '2025-12-30 12:00:05+00',
    timestamptz '2025-12-30 12:15:00+00',
    NULL
  ),
  (
    8,
    'tenant_beta',
    'webhook',
    jsonb_build_object('kind', 'special', 'job', 8),
    'failed',
    45,
    4,
    timestamptz '2025-12-30 18:00:00+00',
    timestamptz '2025-12-30 17:10:00+00',
    'worker-failed',
    timestamptz '2025-12-30 18:00:05+00',
    timestamptz '2025-12-30 18:00:05+00',
    NULL,
    'downstream timeout'
  );

WITH generated_jobs AS (
  SELECT
    gs AS seq,
    gs + 10000 AS id,
    (ARRAY['tenant_alpha', 'tenant_beta', 'tenant_gamma', 'tenant_delta'])[((gs - 1) % 4) + 1] AS tenant_slug,
    (ARRAY['email', 'billing', 'webhook', 'reports'])[((gs - 1) % 4) + 1] AS queue_name,
    CASE
      WHEN gs % 19 = 0 THEN 'processing'
      WHEN gs % 31 = 0 THEN 'completed'
      WHEN gs % 47 = 0 THEN 'failed'
      ELSE 'pending'
    END AS status,
    10 + (gs % 70) AS priority,
    (gs % 4) AS attempts,
    timestamptz '2026-01-10 00:00:00+00'
      + ((gs % 20) * interval '15 minute')
      + ((gs % 7) * interval '1 minute') AS run_at,
    timestamptz '2026-01-09 08:00:00+00'
      + ((gs % 120) * interval '2 minute') AS created_at
  FROM generate_series(1, 90000) AS gs
)
INSERT INTO queue_jobs (
  id,
  tenant_slug,
  queue_name,
  payload,
  status,
  priority,
  attempts,
  run_at,
  created_at,
  locked_by,
  locked_at,
  started_at,
  completed_at,
  last_error
)
SELECT
  g.id,
  g.tenant_slug,
  g.queue_name,
  jsonb_build_object(
    'kind', 'generated',
    'job', g.seq,
    'tenant', g.tenant_slug,
    'queue', g.queue_name
  ),
  g.status,
  g.priority,
  g.attempts,
  g.run_at,
  g.created_at,
  CASE
    WHEN g.status = 'processing' THEN format('worker-%s', (g.seq % 18) + 1)
    WHEN g.status IN ('completed', 'failed') THEN format('worker-%s', (g.seq % 12) + 1)
    ELSE NULL
  END,
  CASE
    WHEN g.status IN ('processing', 'completed', 'failed') THEN g.run_at + interval '30 second'
    ELSE NULL
  END,
  CASE
    WHEN g.status IN ('processing', 'completed', 'failed') THEN g.run_at + interval '30 second'
    ELSE NULL
  END,
  CASE
    WHEN g.status = 'completed' THEN g.run_at + interval '35 minute'
    ELSE NULL
  END,
  CASE
    WHEN g.status = 'failed' THEN 'retry budget exceeded'
    ELSE NULL
  END
FROM generated_jobs AS g;

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
AS $$
  WITH next_job AS (
    SELECT q.id
    FROM queue_jobs AS q
    WHERE q.status = 'pending'
      AND q.run_at <= now()
    ORDER BY q.priority DESC, q.run_at ASC, q.id ASC
    LIMIT 1
    FOR UPDATE
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

GRANT EXECUTE ON FUNCTION claim_next_job(text) TO queue_worker;

VACUUM ANALYZE queue_tenants;
VACUUM ANALYZE queue_jobs;
