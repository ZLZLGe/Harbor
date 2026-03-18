You are helping a ferry operations team review seasonal wildlife slow zones.

Using `/root/ferry_routes.geojson` and `/root/seasonal_slow_zones.geojson`, consider only the slow-zone polygons where `season` is `spring`.

Merge those spring polygons into a single union geometry before measuring route overlap so any shared area is counted only once.

For each ferry route:

1. Compute the total route length that lies inside the spring slow-zone union using the projected metric CRS `EPSG:32648`.
2. Collect the sorted unique `zone_id` values for the spring slow zones that intersect that route.

Then find the single route with the greatest overlap length and write `/root/ferry_slowzone_overlap.json` with exactly these top-level fields:

- `season`
- `route_id`
- `route_name`
- `operator`
- `intersecting_zone_ids`
- `overlap_length_km`

Additional requirements:

- `season` must be the literal string `spring`.
- `intersecting_zone_ids` must contain each matching spring `zone_id` once, sorted ascending.
- `overlap_length_km` must be rounded to 2 decimal places.
- If two routes tie on overlap length, choose the lexicographically smaller `route_id`.
