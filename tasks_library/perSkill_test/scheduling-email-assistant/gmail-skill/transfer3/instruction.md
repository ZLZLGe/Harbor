You are preparing local escalation emails for compliance.

Input files in `/root/data/`:
1. `transfer3_escalation_plan.json`

Available mailbox state in `/root/mailbox/`.

Produce this file in `/root/`:
1. `transfer3_escalation_log.json`

Requirements:
1. Read each listed source message in plan order.
2. Send one escalation email per source message to `compliance.board@example.com`.
3. Use `Escalation: {original subject}` as the outgoing subject.
4. Use this exact body template:
   `Escalation reason: {reason}`
   `Original sender: {original_sender}`
   `Original subject: {original_subject}`
   blank line
   `Original message:`
   `{original_body}`
5. Write `/root/transfer3_escalation_log.json` with:
   - `batch_id`
   - `sent_results`
   - `tool_called`
6. `sent_results` must keep plan order and contain:
   - `source_message_id`
   - `messageId`
7. Set `tool_called` to `["gmail_read", "gmail_send"]`.
