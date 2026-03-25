You are given two inputs:

- `/root/data/network_inventory.xml`: a StationXML inventory that defines the channels that belong in the audit.
- `/root/data/network_window.mseed`: waveform records collected for the same network during the audit window.

Your task is to write `/root/network_availability.json`, a grouped availability report for every channel listed in the StationXML file.

Rules:

1. Read every channel from the StationXML inventory and include it in the report, even if that channel has no waveform records.
2. Match waveform records to channels by the exact `(network, station, location, channel)` code.
3. For each channel, compute:
   - `trace_id`: `NET.STA.LOC.CHA`, keeping the empty location code as an empty segment such as `CI.CCC..HHE`
   - `location`
   - `channel`
   - `sample_rate_hz`
   - `trace_count`
   - `coverage_seconds`
   - `has_waveform_data`
   - `response_complete`
4. `coverage_seconds` must be the sum of `trace.stats.npts / trace.stats.sampling_rate` across all matched traces for that channel.
5. `trace_count` is the number of matched traces.
6. `has_waveform_data` is `true` when `trace_count > 0`, otherwise `false`.
7. `sample_rate_hz` must come from the waveform traces when data exists for that channel. If no waveform records exist, use the sample rate from the inventory metadata.
8. `response_complete` is `true` only when the inventory channel contains a response with a non-null instrument sensitivity value. Otherwise it is `false`.
9. Group channels by station and sort:
   - stations by station code ascending
   - channels within each station by `(location, channel)` ascending

Write UTF-8 JSON with exactly this top-level structure:

```json
{
  "network": "CI",
  "stations": [
    {
      "station": "CCC",
      "channel_count": 2,
      "channels_with_waveforms": 2,
      "total_coverage_seconds": 0.0,
      "channels": [
        {
          "trace_id": "CI.CCC..HHE",
          "location": "",
          "channel": "HHE",
          "sample_rate_hz": 100.0,
          "trace_count": 1,
          "coverage_seconds": 0.0,
          "has_waveform_data": true,
          "response_complete": true
        }
      ]
    }
  ],
  "summary": {
    "channel_count": 6,
    "channels_with_waveforms": 4,
    "channels_missing_response": 2,
    "total_coverage_seconds": 0.0
  }
}
```

Field requirements:

- `channel_count` is the number of reported channels for that station.
- `channels_with_waveforms` at the station level counts channels whose `has_waveform_data` is `true`.
- `total_coverage_seconds` at the station level is the sum of `coverage_seconds` for that station's channels.
- `summary.channel_count` is the total number of reported channels.
- `summary.channels_with_waveforms` is the total number of channels whose `has_waveform_data` is `true`.
- `summary.channels_missing_response` is the total number of channels whose `response_complete` is `false`.
- `summary.total_coverage_seconds` is the sum of `coverage_seconds` across all reported channels.

The verifier will check the JSON structure, grouping, sort order, exact channel membership, and that coverage, sample-rate, and response-completeness values are consistent with the provided StationXML and MiniSEED inputs.
