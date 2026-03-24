# Text normalization contract

`normalize_text` prepares short user-facing labels before they are stored.

The function must:

- trim leading and trailing whitespace,
- collapse internal whitespace runs to a single ASCII space,
- preserve word boundaries across tabs, newlines, and non-breaking spaces,
- convert unicode dashes (`—` and `–`) into a space-padded ASCII hyphen (` - `).

Examples:

- `"  Monthly   Summary  "` -> `"Monthly Summary"`
- `"Quarterly\nStatus"` -> `"Quarterly Status"`
- `"Client\u00a0Update"` -> `"Client Update"`
- `"Roadmap—Phase 2"` -> `"Roadmap - Phase 2"`
