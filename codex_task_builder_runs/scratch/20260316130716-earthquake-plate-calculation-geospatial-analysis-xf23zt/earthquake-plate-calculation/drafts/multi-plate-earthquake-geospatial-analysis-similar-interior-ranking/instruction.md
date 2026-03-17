You are a geospatial analyst reviewing 2024 earthquake activity across several tectonic plates.

Using `/root/earthquakes_2024.json`, `/root/PB2002_plates.json`, and `/root/PB2002_boundaries.json`, compare these four plates only:

- Pacific
- Nazca
- Philippine Sea
- Cocos

For each of the four plates:

1. Find the earthquakes that occurred strictly within that plate polygon.
2. Measure each earthquake's distance to that same plate's own PB2002 boundary lines using a projected metric CRS.
3. Select the single earthquake that is farthest from the plate's own boundary.

Then rank the four per-plate winners from largest `distance_km` to smallest and write the final result to `/root/plate_interior_winner.json`.

The JSON output must have exactly these top-level fields:

- `winning_plate`: object with `plate_code` and `plate_name`
- `winning_earthquake`: object with `id`, `place`, `time`, `magnitude`, `latitude`, and `longitude`
- `winning_distance_km`: numeric distance in kilometers rounded to 2 decimal places
- `plate_rankings`: array of 4 objects sorted by descending `distance_km`

Each object inside `plate_rankings` must contain:

- `plate_code`
- `plate_name`
- `earthquake_count_inside`
- `id`
- `place`
- `time`
- `magnitude`
- `latitude`
- `longitude`
- `distance_km`

Format `time` as UTC ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). Round every reported `distance_km` to 2 decimal places.
