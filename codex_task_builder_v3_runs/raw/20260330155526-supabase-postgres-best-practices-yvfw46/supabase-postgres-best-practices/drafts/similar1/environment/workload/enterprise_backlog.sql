SELECT
  customer_id,
  name,
  segment,
  open_ticket_count,
  high_priority_open_tickets,
  to_char(oldest_open_ticket_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS oldest_open_ticket_at_utc
FROM dashboard_enterprise_backlog
ORDER BY high_priority_open_tickets DESC, oldest_open_ticket_at, customer_id
LIMIT 20;
