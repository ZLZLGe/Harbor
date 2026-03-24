You are preparing a handoff package for a volcano observatory. The input data lives in `/root/data/`.

Files:

- `/root/data/station_registry.json` defines the audit window and the registered stations.
- `/root/data/fragments/*.npz` are fragmented waveform bundles. Each bundle contains:
  - `network`, `station`, `location`
  - `start_time` as an ISO-8601 UTC string
  - `dt` in seconds
  - `channels` as an array of channel codes aligned to the columns of `data`
  - `data` with shape `(npts, n_channels)`

Task:

1. Read the registry and every fragment file.
2. Build one waveform collection per registered station.
3. Ignore fragments for stations not present in the registry.
4. Ignore any channel that is not listed in that station's `expected_channels`.
5. For every kept trace, treat its interval as:
   - `start = start_time`
   - `end = start_time + npts * dt`
   - `end` is exclusive
6. Merge fragments channel-by-channel inside each station:
   - overlapping fragments must merge
   - exactly adjacent fragments must also merge
7. After channel-level merging, compute station coverage intervals as the intersection of all merged interval lists for the station's expected channels.
   - If any expected channel has no data, the station has no coverage intervals.
   - Clip coverage to the audit window from the registry.
8. For each station, compute hourly coverage across the 24 UTC hours in the audit window.
   - `hourly_coverage_seconds` must be a 24-element array.
   - Element `i` is the number of covered seconds inside hour `i`.
9. For each station, compute the first missing interval inside the audit window after subtracting the station coverage intervals.
   - Use the earliest gap in time order.
   - If the station is fully covered for the whole audit window, write `null`.

Write `/root/volcano_gap_report.json` with this structure:

```json
{
  "audit_window_start": "ISO-8601 UTC",
  "audit_window_end": "ISO-8601 UTC",
  "station_count": 0,
  "stations": [
    {
      "network": "VG",
      "station": "ACR",
      "location": "",
      "station_name": "Ash Crater Rim",
      "volcano_name": "Mount Kalama",
      "expected_channels": ["DPE", "DPN", "DPZ"],
      "merged_channel_interval_counts": {
        "DPE": 0,
        "DPN": 0,
        "DPZ": 0
      },
      "coverage_interval_count": 0,
      "coverage_intervals": [
        {
          "start": "ISO-8601 UTC",
          "end": "ISO-8601 UTC",
          "duration_sec": 0.0
        }
      ],
      "hourly_coverage_seconds": [0.0],
      "total_covered_seconds": 0.0,
      "first_missing_interval": {
        "start": "ISO-8601 UTC",
        "end": "ISO-8601 UTC",
        "duration_sec": 0.0
      }
    }
  ]
}
```

Additional requirements:

- Sort `stations` by `network`, `station`, `location`.
- Sort each station's `coverage_intervals` by start time.
- Keep numeric durations in seconds.
- Preserve the station metadata from the registry in the output.
