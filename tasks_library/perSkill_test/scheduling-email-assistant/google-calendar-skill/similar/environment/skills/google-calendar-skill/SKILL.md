---
name: google-calendar-skill
description: Manage the bundled local calendar through lightweight CLI scripts for listing events.
---

# Google Calendar Skill

This task-local skill inspects the bundled calendar state through JSON-producing CLI scripts.

## Usage

```bash
cd ~/.codex/skills/google-calendar-skill/scripts
node calendar-events-list.js --timeMin "2026-01-08T10:00:00Z" --timeMax "2026-01-08T14:00:00Z"
```
