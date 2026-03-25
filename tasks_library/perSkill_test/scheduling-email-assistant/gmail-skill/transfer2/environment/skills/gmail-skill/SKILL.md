---
name: gmail-skill
description: Read messages and manage drafts in the bundled local mailbox through lightweight CLI scripts.
---

# Gmail Manager Skill

This task-local skill provides draft management for the bundled mailbox.

## Usage

```bash
cd ~/.codex/skills/gmail-skill/scripts
node gmail-read.js --id "cand-3001"
node gmail-drafts.js --action create --to "candidate@example.com" --subject "..." --body "..."
node gmail-drafts.js --action list
```
