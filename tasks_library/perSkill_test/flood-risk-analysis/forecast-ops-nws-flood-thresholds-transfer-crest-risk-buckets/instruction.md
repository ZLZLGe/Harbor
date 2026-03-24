Review `/root/data/station_watchlist.csv`, `/root/data/forecast_crest_guidance.json`, and `/root/data/gauge_threshold_export.csv`.

The threshold export uses a bulk gauge format where each data row has one trailing field beyond the header row. For every watchlist station, use only forecast points from the issue time through the next 48 hours, inclusive, to find that station's forecast crest.

Compare the 48-hour crest against these threshold columns: `action stage`, `flood stage`, `moderate flood stage`, and `major flood stage`. Treat `flood stage` as the `minor` threshold in the output. Assign each station to exactly one bucket:

- `no_risk`: crest is below `action stage`
- `action`: crest is at or above `action stage` but below `flood stage`
- `minor`: crest is at or above `flood stage` but below `moderate flood stage`
- `moderate`: crest is at or above `moderate flood stage` but below `major flood stage`
- `major`: crest is at or above `major flood stage`

Write `/root/output/forecast_crest_risk.json` as a JSON object with exactly these top-level keys: `issued_at`, `window_end`, and `buckets`.

`buckets` must contain exactly these five keys: `no_risk`, `action`, `minor`, `moderate`, and `major`. Each bucket value must be a list sorted by `station_id`. Every station object in those lists must contain exactly these keys:

- `station_id`
- `location_name`
- `crest_valid_time`
- `forecast_crest_ft`
- `reference_threshold`
- `threshold_ft`
- `margin_ft`

`reference_threshold` must be one of `action`, `minor`, `moderate`, or `major`, matching the threshold used for that bucket. `margin_ft` is `forecast_crest_ft - threshold_ft`, rounded to one decimal place.
