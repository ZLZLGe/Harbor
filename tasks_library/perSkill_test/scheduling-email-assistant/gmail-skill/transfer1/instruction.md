You are triaging a local vendor inbox.

Input files in `/root/data/`:
1. `transfer1_triage_rules.json`

Available mailbox state in `/root/mailbox/`.

Produce this file in `/root/`:
1. `transfer1_triage_report.json`

Requirements:
1. Apply each triage rule in the listed order.
2. For each rule, search the mailbox using the bundled query, inspect matching messages, and add the requested label to every message whose body contains the required phrase.
3. Write `/root/transfer1_triage_report.json` with this structure:
   - `board_id`
   - `applied_actions`
   - `tool_called`
4. `applied_actions` must keep rule order and contain objects with:
   - `rule_id`
   - `message_id`
   - `subject`
   - `added_label`
   - `summary_line`
5. `summary_line` must be the first sentence of the original message body.
6. Set `tool_called` to `["gmail_search", "gmail_read", "gmail_labels"]`.
