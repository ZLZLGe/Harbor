# Build A Python-to-Scala Syntax Reference

You are given curated Python syntax snippets in `/root/mapping_cases.json`.

Create exactly one file:
- `/outputs/syntax_mapping_reference.json`

Output contract:
1. The output must be a JSON array.
2. Each element must include these fields: `case_id`, `category`, `python`, `scala`.
3. Keep the same item order as in `mapping_cases.json`.
4. Translate each Python snippet to an idiomatic Scala equivalent.
5. Do not add extra fields.

Success criteria:
- `/outputs/syntax_mapping_reference.json` exists and matches the required translations.
