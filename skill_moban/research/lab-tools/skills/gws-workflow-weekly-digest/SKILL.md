# workflow +weekly-digest

> **PREREQUISITE:** Read `../gws-shared/SKILL.md` for auth, global flags, and security rules. If missing, run `gws generate-skills` to create it.

Weekly summary: this week's meetings + unread email count

## Usage

```bash
gws workflow +weekly-digest

```

## Flags

| Flag      | Required | Default | Description                                     |
| --------- | -------- | ------- | ----------------------------------------------- |
| \--format | —        | —       | Output format: json (default), table, yaml, csv |

## Examples

```bash
gws workflow +weekly-digest
gws workflow +weekly-digest --format table

```

## Tips

* Read-only — never modifies data.
* Combines calendar agenda (week) with gmail triage summary.

## See Also

* [gws-shared](https://github.com/googleworkspace/cli/blob/HEAD/skills/gws-workflow-weekly-digest/../gws-shared/SKILL.md) — Global flags and auth
* [gws-workflow](https://github.com/googleworkspace/cli/blob/HEAD/skills/gws-workflow-weekly-digest/../gws-workflow/SKILL.md) — All cross-service productivity workflows commands
