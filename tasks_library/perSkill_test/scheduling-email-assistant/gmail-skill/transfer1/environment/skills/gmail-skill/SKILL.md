---
name: gmail-skill
description: Search, read, and label messages in the bundled local mailbox through lightweight CLI scripts.
---

# Gmail Manager Skill

This task-local skill manages the bundled mailbox state with small JSON-producing scripts.

## Usage

```bash
cd ~/.codex/skills/gmail-skill/scripts
node gmail-search.js --query "label:INBOX is:unread"
node gmail-read.js --id "vend-2001"
node gmail-labels.js --action add --id "vend-2001" --label "UrgentVendor"
```
