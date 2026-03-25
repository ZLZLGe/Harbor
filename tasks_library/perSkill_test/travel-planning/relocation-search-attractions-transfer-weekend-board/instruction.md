## Task
Read `/app/data/relocation_candidates.toml` and `/app/data/weekend_board_rules.json`, then build a relocation weekend comparison board for the listed finalist cities.

Write a single HTML file to `/app/output/relocation_weekend_board.html`.

## Input
`/app/data/relocation_candidates.toml` contains:
- `page_title`: the board title
- `intro_note`: one introductory sentence for the page
- `cities`: ordered city entries, each with `city`, `label`, and `weekend_angle`

`/app/data/weekend_board_rules.json` contains:
- `group_order`: the exact attraction group order to render for every city
- `cards_per_group`: how many attraction cards each group must contain
- `link_text`: the exact visible text to use for every attraction website link

## Output format
The HTML must include:
- a `<title>` equal to `page_title`
- one top-level `<h1>` equal to `page_title`
- one `<p id="board-intro">` equal to `intro_note`
- one `<main id="relocation-weekend-board">`

Inside that main element, render one `<section class="city-board" data-city="<city>">` for each city in the exact order from `relocation_candidates.toml`.

Each city section must contain:
- one `<h2>` equal to that city's `label`
- one `<p class="weekend-angle">` equal to that city's `weekend_angle`
- one `<div class="group-column" data-group="<group>">` for each group in `group_order`, preserving that order

Each group column must contain exactly the number of `<article class="attraction-card">` elements required by `cards_per_group`.

Each attraction card must contain:
- one element with class `attraction-name`
- one element with class `attraction-address`
- one link whose visible text is exactly `link_text` and whose `href` is the attraction website

## Rules
- The total number of cards per city must equal the sum of all values in `cards_per_group`.
- Every attraction listed for a city must come from the attraction data for that exact city.
- Copy each attraction name, address, and website exactly from the source data. Do not rewrite or normalize them.
- Within a single city section, do not repeat the same attraction name across different groups.
- Do not add extra city sections or extra attraction cards.
