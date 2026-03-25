You are working through a local mailbox of meeting requests.

Input files in `/root/data/`:
1. `similar_reply_plan.json`

Available mailbox state in `/root/mailbox/`.

Produce this file in `/root/`:
1. `similar_sent_results.json`

Requirements:
1. For each entry in `similar_reply_plan.json`, read the original message from the mailbox and reply to the original sender.
2. Use this exact body template for every reply:
   `Hi,`
   blank line
   `Thank you for your meeting request.`
   blank line
   `I can be available:`
   blank line
   `Date: {date}`
   `Time: {time}`
   `Duration: {duration_hours} hour(s)`
   blank line
   `If this time doesn't work, please let me know your preferred alternatives.`
   blank line
   `Best regards,`
   `Ops Desk`
3. Use the original sender as the reply recipient.
4. Use `Re: {original subject}` as the reply subject.
5. Write `/root/similar_sent_results.json` with this structure:
   - `batch_id`
   - `sent_results`
   - `tool_called`
6. `sent_results` must keep the plan order and contain objects with:
   - `request_message_id`
   - `messageId`
7. Set `tool_called` to `["gmail_read", "gmail_send"]`.
