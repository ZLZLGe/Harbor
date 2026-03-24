Review `/root/data/park_gage_assignments.json`, `/root/data/latest_stage_snapshot.csv`, and `/root/data/gauge_threshold_export.csv`.

The park assignment file lists riverfront facilities that have already been mapped to USGS station IDs. Expand advisories at the facility level, not the station level, so if multiple parks share the same station they can each appear separately in the output.

The threshold export follows the bulk gauge format where each data row contains one trailing field beyond the header row. Use the `flood stage` column as the flood threshold. Ignore stations with a blank `usgs id`, a missing `flood stage`, or `flood stage = -9999`.

Match each park's `station_id` against both the threshold export and the latest observed stage snapshot. Generate advisories only for parks whose observed stage is greater than or equal to that station's flood stage.

Write `/root/output/river_access_advisories.json` as a JSON object with exactly these top-level keys:

- `snapshot_time`
- `advisory_count`
- `advisories`

`snapshot_time` must be copied from the `snapshot_time` value in `/root/data/park_gage_assignments.json`. `advisory_count` must equal the number of advisory objects written.

Each advisory object must contain exactly these keys:

- `park_id`
- `station_id`
- `flood_stage_ft`
- `observed_stage_ft`
- `exceedance_ft`

`exceedance_ft` is `observed_stage_ft - flood_stage_ft`, rounded to one decimal place. Sort `advisories` by descending `exceedance_ft`, then ascending `park_id`.
