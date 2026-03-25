## Task
Read `/app/data/conference_cities.csv` and `/app/data/free_time_slots.json`, then prepare a conference free-time brief for the listed host cities.

Write a single Markdown file to `/app/output/conference_free_time_brief.md`.

## Input
`/app/data/conference_cities.csv` contains the city roster in the order the brief should present them.

`/app/data/free_time_slots.json` contains the exact slot names to use and how many attractions to list in each slot.

## Output format
The Markdown file must follow this structure:

- First line: `# Conference Free-Time City Brief`
- Then one `## <city>` section for each city, preserving the CSV order
- Inside each city section, include these exact third-level headings in the order given by `free_time_slots.json`:
  - `### arrival-night`
  - `### open-morning`
  - `### team-dinner-backup`
- Under each slot heading, add the required number of bullet items

Each bullet item must use this exact pattern:

`- <name> | <address> | <website>`

## Rules
- Every listed attraction must come from the attraction data for that exact city.
- Copy each attraction name, address, and website exactly from the source data. Do not rewrite or normalize them.
- Within a single city section, do not repeat the same attraction name across different slots.
- Keep the city sections focused on the requested free-time brief. Extra narrative is optional, but do not change the required headings or bullet format.
