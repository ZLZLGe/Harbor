SELECT
  ticket_id,
  customer_id,
  assignee_id,
  to_char(latest_public_customer_reply_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS latest_public_customer_reply_at_utc,
  latest_public_customer_actor_id
FROM dashboard_latest_customer_reply
WHERE latest_public_customer_reply_at >= timestamptz '2025-02-15 00:00:00+00'
ORDER BY latest_public_customer_reply_at DESC, ticket_id
LIMIT 25;
