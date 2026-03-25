## Task
Read `/app/data/classroom_cities.txt` and `/app/data/card_export_template.json`, then prepare a landmark card dataset for a classroom comparison activity.

Write a single CSV file to `/app/output/landmark_cards.csv`.

## Input
`/app/data/classroom_cities.txt` lists the target cities, one city per line, in the exact order the dataset should present them.

`/app/data/card_export_template.json` defines:
- the exact CSV columns to use
- the exact `card_group` values to emit for every city

## Output format
The CSV header must exactly match the `columns` array from the template file.

Each output row must contain these fields:
- `city`
- `card_group`
- `attraction_name`
- `address`
- `website`

## Rules
- For each city in `classroom_cities.txt`, output exactly 3 rows.
- Within each city block, use the `card_group` values from the template in the exact order they appear.
- Preserve the city order from `classroom_cities.txt`.
- Every attraction must come from the attraction data for that exact city.
- Copy each attraction name, address, and website exactly from the source data. Do not rewrite or normalize them.
- Within a single city, do not repeat the same attraction name across the 3 rows.
- Do not add extra columns or extra rows.
