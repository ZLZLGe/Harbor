SELECT
  id,
  queue_name,
  priority,
  run_at
FROM queue_jobs
WHERE status = 'pending'
  AND run_at <= now()
ORDER BY priority DESC, run_at ASC, id ASC
LIMIT 10;
