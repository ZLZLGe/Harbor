SELECT
  queue_name,
  count(*) AS pending_jobs,
  min(run_at) AS oldest_run_at
FROM queue_jobs
WHERE status = 'pending'
GROUP BY queue_name
ORDER BY queue_name;
