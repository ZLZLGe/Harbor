Review `/root/data/station_roster_mixed.txt` and `/root/data/nws_thresholds_batch.csv`.

The station roster is a messy multi-county text file. Build the target station list by extracting the USGS station ID from each roster line, keeping only digit sequences that resolve to an 8-digit station ID after trimming punctuation and left-padding with zeros when needed. Ignore roster lines that do not contain a usable station ID, and de-duplicate repeated stations after normalization.

The threshold file is a bulk gauge export where every data row contains one trailing field beyond the header row. Match the normalized rostered station IDs against the `usgs id` field. Keep only records with a non-empty `usgs id` and valid numeric values for all four threshold columns: `action stage`, `flood stage`, `moderate flood stage`, and `major flood stage`. Treat blank values and `-9999` as invalid.

Write `/root/output/station_threshold_catalog.csv` with exactly these columns in this order:

- `station_id`
- `location_name`
- `state`
- `action_stage`
- `flood_stage`
- `moderate_stage`
- `major_stage`

Write one row per matched station, sorted by `state` and then `station_id`.
