---
name: gmail-skill
description: Read bundled messages and send local escalation emails through lightweight CLI scripts.
---

# Gmail Manager Skill

This task-local skill supports reading messages and sending new emails through the bundled mailbox state.

## Usage

```bash
cd ~/.codex/skills/gmail-skill/scripts
node gmail-read.js --id "comp-4001"
node gmail-send.js --to "compliance.board@example.com" --subject "..." --body "..."
```
