You are helping a city emergency planning team evaluate heatwave response coverage.

Using `/root/heatwave_alert_zones.geojson`, `/root/community_centers.csv`, and `/root/cooling_centers.csv`, consider only the community centers that fall inside at least one heatwave alert zone polygon.

For each eligible community center:

1. Identify the nearest cooling center using a projected metric CRS.
2. Compute that nearest distance in kilometers.

Then find the single community center whose nearest cooling center distance is the largest.

Write `/root/cooling_access_gap.json` with exactly these top-level fields:

- `alert_zone_id`
- `community_center_id`
- `nearest_cooling_center_id`
- `community_latitude`
- `community_longitude`
- `nearest_distance_km`

Additional requirements:

- If a community center falls inside more than one alert zone, report the lexicographically smallest `alert_zone_id`.
- `community_latitude` and `community_longitude` must be numeric values copied from the winning community center.
- `nearest_distance_km` must be rounded to 2 decimal places.
