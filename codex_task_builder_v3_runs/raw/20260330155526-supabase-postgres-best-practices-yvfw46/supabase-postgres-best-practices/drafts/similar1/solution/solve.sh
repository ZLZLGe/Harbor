#!/bin/bash

set -euo pipefail

cd /workspace
mkdir -p answer

cat > answer/support_dashboard_fix.sql <<'SQL'
create index if not exists tickets_open_by_assignee_idx
  on tickets (assignee_id, first_response_due_at)
  include (priority, last_customer_reply_at)
  where deleted_at is null
    and status in ('new', 'open', 'pending');

create index if not exists tickets_open_by_customer_idx
  on tickets (customer_id, created_at)
  include (priority)
  where deleted_at is null
    and status in ('new', 'open', 'pending');

create index if not exists tickets_open_lookup_idx
  on tickets (id)
  include (customer_id, assignee_id)
  where deleted_at is null
    and status in ('new', 'open', 'pending');

create index if not exists ticket_events_customer_public_latest_idx
  on ticket_events (ticket_id, created_at desc, id desc)
  include (actor_id)
  where actor_type = 'customer'
    and is_public = true;

create or replace view dashboard_latest_customer_reply as
select
  t.id as ticket_id,
  t.customer_id,
  t.assignee_id,
  latest.created_at as latest_public_customer_reply_at,
  latest.actor_id as latest_public_customer_actor_id
from tickets as t
join lateral (
  select
    te.created_at,
    te.actor_id
  from ticket_events as te
  where te.ticket_id = t.id
    and te.actor_type = 'customer'
    and te.is_public = true
  order by te.created_at desc, te.id desc
  limit 1
) as latest on true
where t.status in ('new', 'open', 'pending')
  and t.deleted_at is null;
SQL
