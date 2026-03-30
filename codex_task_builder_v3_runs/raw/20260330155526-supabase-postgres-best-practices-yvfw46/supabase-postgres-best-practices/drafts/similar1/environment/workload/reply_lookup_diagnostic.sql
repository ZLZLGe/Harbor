SELECT
  ticket_id,
  created_at,
  actor_id
FROM ticket_events
WHERE ticket_id = 42017
  AND actor_type = 'customer'
  AND is_public = true
ORDER BY created_at DESC, id DESC
LIMIT 1;
