You are given a small aftershock review package in `/root/data/`.

The inputs are intentionally mixed:

- Event metadata is split across `/root/data/events.csv` and `/root/data/event_updates.json`.
- Station metadata is split across `/root/data/stations.csv` and `/root/data/station_updates.json`.
- Waveforms live in `/root/data/waveforms/` and use three formats:
  - `.npz`: keys `event_id`, `network`, `station`, `location`, `start_time`, `dt`, `channels`, `data`
  - `.json`: keys `event_id`, `network`, `station`, `location`, `start_time`, `dt`, `traces`, where each trace has `channel` and `samples`
  - `.csv`: metadata in leading `# key=value` lines, then rows `sample_index,channel,amplitude`

Your job is to combine these sources into standard seismological objects and produce one arrival-review window per usable station-event pair.

Requirements:

1. Read every event definition and build a unified event collection.
2. Read every station definition and build a unified station collection.
3. Read every waveform file and convert it into a multi-channel trace collection with correct absolute start times and sample rates.
4. Treat a station-event pair as usable only if all of the following are true:
   - the event exists in the unified event metadata
   - the station exists in the unified station metadata
   - the waveform contains at least 2 channels
   - all channels share the same sample rate
   - the waveform overlaps the event review template with positive duration

For each usable pair, compute a review window from the event origin:

- Template start = `origin_time - review_pre_sec`
- Template end = `origin_time + review_post_sec`
- `trace_start` is the latest channel start time
- `trace_end` is the earliest channel-exclusive end time
- `review_start = max(trace_start, template_start)`
- `review_end = min(trace_end, template_end)`

Important:

- Treat both `trace_end` and `review_end` as exclusive bounds.
- Compute each channel's exclusive end as `start_time + npts / sample_rate`.
- `sample_rate_hz` must be the shared sample rate for the usable waveform.
- `window_duration_sec = review_end - review_start`
- `start_offset_sec = review_start - origin_time`
- `end_offset_sec = review_end - origin_time`
- `channel_coverage` must be the waveform's channel codes sorted lexicographically and joined with `|`
- `channel_count` is the number of channels in the usable waveform

Write `/root/arrival_windows.csv` with exactly these columns:

`event_id,network,station,location,waveform_file,origin_time,trace_start,trace_end,review_start,review_end,start_offset_sec,end_offset_sec,sample_rate_hz,window_duration_sec,channel_count,channel_coverage`

Sort the rows by `event_id`, `network`, `station`, `location`, `waveform_file`.
