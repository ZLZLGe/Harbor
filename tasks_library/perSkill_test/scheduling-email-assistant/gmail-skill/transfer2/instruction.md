You are assembling a local batch of follow-up drafts.

Input files in `/root/data/`:
1. `transfer2_follow_up_plan.json`

Available mailbox state in `/root/mailbox/`.

Produce this file in `/root/`:
1. `transfer2_draft_manifest.json`

Requirements:
1. Read each source message in plan order and create one draft reply for it.
2. Use `Re: {original subject}` as the draft subject.
3. Use this exact body template:
   `Hi {candidate_name},`
   blank line
   `Thanks for following up.`
   `Your next step is {next_step}.`
   `Please send any updates by {response_by}.`
   blank line
   `Best,`
   `Talent Ops`
4. Write `/root/transfer2_draft_manifest.json` with:
   - `campaign_id`
   - `drafts`
   - `tool_called`
5. `drafts` must keep plan order and contain:
   - `source_message_id`
   - `draftId`
6. Set `tool_called` to `["gmail_read", "gmail_drafts"]`.
