\set ON_ERROR_STOP on

SET client_min_messages = warning;
SET timezone = 'UTC';

DROP VIEW IF EXISTS dashboard_latest_customer_reply;
DROP VIEW IF EXISTS dashboard_enterprise_backlog;
DROP VIEW IF EXISTS dashboard_agent_load;
DROP TABLE IF EXISTS ticket_events;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS support_customers;
DROP TABLE IF EXISTS support_agents;

CREATE TABLE support_agents (
  id integer PRIMARY KEY,
  name text NOT NULL,
  team text NOT NULL,
  active boolean NOT NULL
);

CREATE TABLE support_customers (
  id integer PRIMARY KEY,
  name text NOT NULL,
  segment text NOT NULL,
  region text NOT NULL
);

CREATE TABLE tickets (
  id bigint PRIMARY KEY,
  customer_id integer NOT NULL REFERENCES support_customers(id),
  assignee_id integer NOT NULL REFERENCES support_agents(id),
  status text NOT NULL,
  priority text NOT NULL,
  channel text NOT NULL,
  subject text NOT NULL,
  created_at timestamptz NOT NULL,
  first_response_due_at timestamptz NOT NULL,
  last_customer_reply_at timestamptz,
  closed_at timestamptz,
  deleted_at timestamptz
);

CREATE TABLE ticket_events (
  id bigint PRIMARY KEY,
  ticket_id bigint NOT NULL REFERENCES tickets(id),
  actor_type text NOT NULL,
  actor_id integer NOT NULL,
  event_type text NOT NULL,
  is_public boolean NOT NULL,
  created_at timestamptz NOT NULL,
  body text NOT NULL
);

INSERT INTO support_agents (id, name, team, active)
SELECT
  gs,
  format('Agent %s', gs),
  CASE gs % 4
    WHEN 0 THEN 'core'
    WHEN 1 THEN 'priority'
    WHEN 2 THEN 'escalations'
    ELSE 'weekend'
  END,
  gs <= 60
FROM generate_series(1, 72) AS gs;

INSERT INTO support_customers (id, name, segment, region)
SELECT
  gs,
  format('Customer %s', gs),
  CASE
    WHEN gs % 8 IN (0, 1) THEN 'enterprise'
    WHEN gs % 8 IN (2, 3, 4) THEN 'growth'
    ELSE 'starter'
  END,
  CASE gs % 5
    WHEN 0 THEN 'na'
    WHEN 1 THEN 'emea'
    WHEN 2 THEN 'apac'
    WHEN 3 THEN 'latam'
    ELSE 'mea'
  END
FROM generate_series(1, 2400) AS gs;

WITH base_tickets AS (
  SELECT
    gs AS id,
    1 + (gs % 2400) AS customer_id,
    1 + (gs % 60) AS assignee_id,
    CASE
      WHEN gs % 30 = 0 THEN 'new'
      WHEN gs % 10 = 0 THEN 'pending'
      WHEN gs % 6 = 0 THEN 'open'
      WHEN gs % 2 = 0 THEN 'resolved'
      ELSE 'closed'
    END AS status,
    CASE
      WHEN gs % 20 = 0 THEN 'urgent'
      WHEN gs % 5 = 0 THEN 'high'
      WHEN gs % 2 = 0 THEN 'normal'
      ELSE 'low'
    END AS priority,
    CASE gs % 4
      WHEN 0 THEN 'email'
      WHEN 1 THEN 'chat'
      WHEN 2 THEN 'phone'
      ELSE 'web'
    END AS channel,
    timestamptz '2025-01-01 08:00:00+00'
      + ((gs % 120) * interval '1 day')
      + ((gs % 720) * interval '2 minute') AS created_at
  FROM generate_series(1, 60000) AS gs
)
INSERT INTO tickets (
  id,
  customer_id,
  assignee_id,
  status,
  priority,
  channel,
  subject,
  created_at,
  first_response_due_at,
  last_customer_reply_at,
  closed_at,
  deleted_at
)
SELECT
  id,
  customer_id,
  assignee_id,
  status,
  priority,
  channel,
  format('Ticket %s', id),
  created_at,
  created_at + interval '4 hours' + ((id % 5) * interval '15 minutes'),
  created_at + interval '75 minutes' + ((id % 12) * interval '10 minutes'),
  CASE
    WHEN status IN ('resolved', 'closed') THEN created_at + interval '2 days' + ((id % 6) * interval '45 minutes')
    ELSE NULL
  END,
  CASE
    WHEN id % 97 = 0 THEN created_at + interval '10 days'
    ELSE NULL
  END
FROM base_tickets;

INSERT INTO ticket_events (
  id,
  ticket_id,
  actor_type,
  actor_id,
  event_type,
  is_public,
  created_at,
  body
)
SELECT
  ((t.id - 1) * 4) + e.step AS id,
  t.id,
  CASE e.step
    WHEN 1 THEN 'customer'
    WHEN 2 THEN 'agent'
    WHEN 3 THEN 'system'
    ELSE 'customer'
  END,
  CASE e.step
    WHEN 1 THEN ((t.customer_id * 17) % 5000) + 1
    WHEN 2 THEN t.assignee_id
    WHEN 3 THEN 0
    ELSE ((t.customer_id * 17 + 11) % 5000) + 1
  END,
  CASE
    WHEN e.step = 3 THEN 'status_change'
    ELSE 'comment'
  END,
  e.step <> 3,
  t.created_at + (e.step * interval '6 hours') + ((t.id % 7) * interval '5 minutes'),
  format('Ticket %s event %s', t.id, e.step)
FROM tickets AS t
CROSS JOIN generate_series(1, 4) AS e(step);

CREATE VIEW dashboard_agent_load AS
SELECT
  a.id AS agent_id,
  a.name,
  a.team,
  count(*) FILTER (WHERE t.priority = 'urgent') AS urgent_open_tickets,
  count(*) AS total_open_tickets,
  min(t.first_response_due_at) AS next_sla_deadline,
  max(t.last_customer_reply_at) AS latest_customer_reply_at
FROM support_agents AS a
JOIN tickets AS t
  ON t.assignee_id = a.id
WHERE a.active = true
  AND t.status IN ('new', 'open', 'pending')
  AND t.deleted_at IS NULL
GROUP BY a.id, a.name, a.team;

CREATE VIEW dashboard_enterprise_backlog AS
SELECT
  c.id AS customer_id,
  c.name,
  c.segment,
  count(*) AS open_ticket_count,
  count(*) FILTER (WHERE t.priority IN ('high', 'urgent')) AS high_priority_open_tickets,
  min(t.created_at) AS oldest_open_ticket_at
FROM support_customers AS c
JOIN tickets AS t
  ON t.customer_id = c.id
WHERE c.segment IN ('growth', 'enterprise')
  AND t.status IN ('new', 'open', 'pending')
  AND t.deleted_at IS NULL
GROUP BY c.id, c.name, c.segment
HAVING count(*) >= 3;

CREATE VIEW dashboard_latest_customer_reply AS
WITH ranked_events AS (
  SELECT
    te.ticket_id,
    te.actor_type,
    te.actor_id,
    te.is_public,
    te.created_at,
    row_number() OVER (
      PARTITION BY te.ticket_id
      ORDER BY te.created_at DESC, te.id DESC
    ) AS rn
  FROM ticket_events AS te
)
SELECT
  t.id AS ticket_id,
  t.customer_id,
  t.assignee_id,
  re.created_at AS latest_public_customer_reply_at,
  re.actor_id AS latest_public_customer_actor_id
FROM tickets AS t
JOIN ranked_events AS re
  ON re.ticket_id = t.id
 AND re.rn = 1
WHERE t.status IN ('new', 'open', 'pending')
  AND t.deleted_at IS NULL
  AND re.actor_type = 'customer'
  AND re.is_public = true;

VACUUM ANALYZE support_agents;
VACUUM ANALYZE support_customers;
VACUUM ANALYZE tickets;
VACUUM ANALYZE ticket_events;
