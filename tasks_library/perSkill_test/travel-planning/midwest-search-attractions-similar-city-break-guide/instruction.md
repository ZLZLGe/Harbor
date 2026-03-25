## Task
Read `/app/data/city_break_request.json` and build a city-break attraction guide for the listed Midwest cities.

Write a single JSON file to `/app/output/city_break_guide.json`.

## Input
The request file contains:
- `trip_name`: overall label for the guide
- `city_stays`: ordered list of city stops, each with `city`, `days`, and `focus_keywords`
- `selection_rules`: how many attractions to place in each time block

## Output format
The JSON file must be an object with:
- `trip_name`: copy the value from the request file exactly
- `days`: array of day objects in the same city order as `city_stays`

Each day object must contain:
- `day`: sequential integer starting at 1
- `current_city`: exact city name for that day
- `focus`: short text that includes at least one keyword from that city's `focus_keywords`
- `morning_attractions`: array of attraction objects
- `afternoon_attractions`: array of attraction objects
- `evening_attractions`: array of attraction objects

Each attraction object must contain:
- `name`
- `address`
- `website`

## Rules
- Expand the guide into one day object per requested day, preserving the city order from the request file.
- For every day, the number of attractions in the morning, afternoon, and evening arrays must match `selection_rules.morning_count`, `selection_rules.afternoon_count`, and `selection_rules.evening_count`.
- Every attraction entry must come from the attraction results for that exact `current_city`.
- Copy the address and website exactly from the attraction data. Do not invent or normalize them.
- Do not repeat the same attraction name within a single day.
