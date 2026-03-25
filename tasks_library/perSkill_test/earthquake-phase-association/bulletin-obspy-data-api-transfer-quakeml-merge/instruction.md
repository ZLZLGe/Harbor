You are given a directory tree of regional earthquake metadata fragments in QuakeML format under `/root/data/quakeml_fragments/`.

Your task is to merge those fragments into one bulletin file at `/root/regional_bulletin.csv`.

Requirements:

1. Recursively read every `.xml` file under `/root/data/quakeml_fragments/`.
2. For each event, extract one origin:
   - Use the event's preferred origin when it exists.
   - Otherwise use the earliest origin time in that event.
3. For each event, extract one magnitude:
   - Use the event's preferred magnitude when it exists.
   - Otherwise use the first magnitude listed in that event.
4. Normalize the event identifier by taking the last path token of the event resource ID and stripping a trailing revision suffix of the form `-rev<number>`.
5. Build one candidate bulletin row per event with these fields:
   - `event_id`
   - `time`
   - `latitude`
   - `longitude`
   - `depth_km`
   - `magnitude`
   - `magnitude_type`
   - `source_count`
6. Deduplicate candidates using the pair:
   - normalized `event_id`
   - the chosen origin time truncated to whole seconds
7. When duplicates share the same deduplication key, keep the most recently updated candidate:
   - first use the chosen origin's creation time if present
   - otherwise use the event creation time if present
   - otherwise fall back to the chosen origin time
   - `source_count` must equal the number of merged candidates for that final row
8. Convert depth from meters to kilometers.
9. Sort the final bulletin by `time` ascending, breaking ties by `event_id`.

Write `/root/regional_bulletin.csv` with exactly the eight columns listed above.

Formatting rules:

- `time` must be ISO format without a timezone suffix, for example `2024-04-01T02:45:01.850000`
- Numeric columns must remain numeric in the CSV
- `source_count` must be an integer

The verifier will check:

- the output columns and sort order
- that duplicates were merged correctly
- exact values for several focus events, including preferred-origin and preferred-magnitude handling
