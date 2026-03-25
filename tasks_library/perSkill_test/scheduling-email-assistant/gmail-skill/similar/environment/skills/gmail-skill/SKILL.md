---
name: gmail-skill
description: Manage local mailbox messages, including reading and sending replies, through lightweight CLI scripts.
---

# Gmail Manager Skill

This task-local skill provides Gmail-like mailbox operations through small CLI scripts that read and update the bundled mailbox state.

## Usage

Change into the scripts directory when needed:

```bash
cd ~/.codex/skills/gmail-skill/scripts
```

### Read a message

```bash
node gmail-read.js --id "msg-1001"
```

### Send a message

```bash
node gmail-send.js --to "user@example.com" --subject "Subject" --body "Body text"
```

All scripts return JSON.
