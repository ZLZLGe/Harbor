# workflow +meeting-prep

> **PREREQUISITE:** Read `../gws-shared/SKILL.md` for auth, global flags, and security rules. If missing, run `gws generate-skills` to create it.

Prepare for your next meeting: agenda, attendees, and linked docs

## Usage

```bash
gws workflow +meeting-prep

```

## Flags

| Flag        | Required | Default | Description                                     |
| ----------- | -------- | ------- | ----------------------------------------------- |
| \--calendar | —        | primary | Calendar ID (default: primary)                  |
| \--format   | —        | —       | Output format: json (default), table, yaml, csv |

## Examples

```bash
gws workflow +meeting-prep
gws workflow +meeting-prep --calendar Work

```

## Tips

* Read-only — never modifies data.
* Shows the next upcoming event with attendees and description.

## See Also

* [gws-shared](https://github.com/googleworkspace/cli/blob/HEAD/skills/gws-workflow-meeting-prep/../gws-shared/SKILL.md) — Global flags and auth
* [gws-workflow](https://github.com/googleworkspace/cli/blob/HEAD/skills/gws-workflow-meeting-prep/../gws-workflow/SKILL.md) — All cross-service productivity workflows commands
