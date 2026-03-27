# Generate A Scala Migration Playbook

Structured mapping data is provided at `/root/playbook_sections.json`.

Create exactly one file:
- `/outputs/syntax_mapping_playbook.md`

Output contract:
1. The first line must be `# Python to Scala Migration Playbook`.
2. For each section in input order, emit:
   - `## <section>`
   - a markdown table with header `| Python | Scala |`
   - separator row `|---|---|`
3. Each mapping row must use inline code formatting, for example:
   `| \`x = 5\` | \`val x = 5\` |`
4. Keep the exact entry order within each section.

Success criteria:
- `/outputs/syntax_mapping_playbook.md` exists and matches the required format and content.
