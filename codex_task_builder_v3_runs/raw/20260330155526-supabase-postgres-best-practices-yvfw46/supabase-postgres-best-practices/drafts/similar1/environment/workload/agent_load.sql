SELECT
  agent_id,
  name,
  team,
  urgent_open_tickets,
  total_open_tickets,
  to_char(next_sla_deadline AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS next_sla_deadline_utc,
  to_char(latest_customer_reply_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS latest_customer_reply_at_utc
FROM dashboard_agent_load
WHERE team IN ('core', 'priority')
ORDER BY urgent_open_tickets DESC, total_open_tickets DESC, agent_id
LIMIT 15;
