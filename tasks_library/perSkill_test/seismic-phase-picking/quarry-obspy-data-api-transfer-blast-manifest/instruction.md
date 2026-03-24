You are preparing an analyst handoff for a quarry blast review package in `/root/data/`.

Inputs:

- `/root/data/events/quarry_blasts.xml`: blast event metadata in QuakeML.
- `/root/data/stations/quarry_inventory.xml`: station metadata in StationXML.
- `/root/data/waveforms/*.npz`: waveform snippets. Each snippet contains:
  - `event_id`
  - `network`
  - `station`
  - `location`
  - `dt` in seconds
  - `channels`: channel codes aligned to the columns of `data`
  - `start_times`: one ISO-8601 UTC timestamp per channel
  - `sample_counts`: one sample count per channel
  - `data`: a 2-D array shaped `(max_npts, n_channels)` with trailing `NaN` padding beyond each channel's `sample_counts`

Your job is to reconcile these assets into standard seismological objects and write a station manifest for every usable blast snippet.

Required rules:

1. Load the blast catalog from the QuakeML file.
2. Load the station inventory from the StationXML file.
3. For each waveform snippet, build a multi-trace waveform object using:
   - one trace per channel
   - `start_times[i]` as the trace start time
   - `sample_counts[i]` to trim each channel before discarding the trailing padding
   - `sample_rate_hz = 1 / dt`
4. Resolve the blast for a snippet by matching `event_id` to the suffix of an event public ID in the catalog.
5. Resolve the recording station by matching the snippet's `network`, `station`, and `location` to the inventory.
6. A snippet is usable only if all of the following are true:
   - the blast resolves to exactly one event
   - the station resolves in the inventory
   - the snippet has at least 2 channels
   - all channels share the same sample rate
   - every channel code exists for that station and location in the inventory
   - every matched inventory channel has the same sample rate as the snippet
   - the common snippet interval has positive duration
   - the blast origin time falls within the common snippet interval, treating the end as exclusive
7. Use the event's preferred origin if present, otherwise its first origin.
8. Use the event's preferred magnitude if present, otherwise its first magnitude; if no magnitude exists, write `null`.
9. Use the station object's latitude, longitude, and elevation for station coordinates.
10. For every usable snippet, compute:
    - `trace_start` as the latest channel start time
    - `trace_end` as the earliest exclusive channel end time, where each channel end is `start_time + sample_count / sample_rate_hz`
    - `trace_start_offset_sec = trace_start - event_time`
    - `trace_duration_sec = trace_end - trace_start`
    - `channel_set` as the snippet's channel codes sorted lexicographically

Write `/root/blast_station_manifest.json` with exactly this structure:

```json
{
  "quarry_name": "Basalt Ridge Quarry",
  "record_count": 0,
  "records": [
    {
      "event_id": "blast_alpha",
      "event_time": "ISO-8601 UTC",
      "event_latitude": 0.0,
      "event_longitude": 0.0,
      "event_depth_m": 0.0,
      "event_magnitude": 0.0,
      "station_network": "QB",
      "station_code": "RIM1",
      "station_location": "",
      "station_latitude": 0.0,
      "station_longitude": 0.0,
      "station_elevation_m": 0.0,
      "waveform_file": "blast_alpha_rim1.npz",
      "trace_start": "ISO-8601 UTC",
      "trace_start_offset_sec": 0.0,
      "trace_duration_sec": 0.0,
      "sample_rate_hz": 0.0,
      "channel_set": ["HHE", "HHN", "HHZ"]
    }
  ]
}
```

Additional requirements:

- Sort `records` by `event_time`, `station_network`, `station_code`, `station_location`, `waveform_file`.
- Use UTC ISO-8601 timestamps with a trailing `Z` and six digits of fractional seconds.
- Keep numeric values in seconds or meters as numbers, not strings.
