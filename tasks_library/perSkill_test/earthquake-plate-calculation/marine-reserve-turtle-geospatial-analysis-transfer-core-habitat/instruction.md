You are helping a marine reserve monitoring team review turtle satellite pings.

Using `/root/pelagia_turtle_pings.csv`, `/root/pelagia_marine_reserve.geojson`, and `/root/pelagia_reserve_boundary.geojson`, identify the single turtle observation that is strictly inside the marine reserve polygon and farthest from the reserve boundary.

Use a projected metric CRS for the distance calculation. Then write `/root/turtle_core_ping.json` with exactly these top-level fields:

- `tag_id`
- `observed_at`
- `latitude`
- `longitude`
- `distance_km`

Additional requirements:

- `observed_at` must remain in UTC ISO 8601 format exactly as provided in the input.
- `distance_km` must be rounded to 2 decimal places.
- `latitude` and `longitude` must be numeric values copied from the winning observation.
