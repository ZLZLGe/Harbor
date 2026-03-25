You are given three inputs:

- `/root/data/ridgecrest_hour.mseed`: one hour of continuous Ridgecrest waveforms.
- `/root/data/stations_subset.csv`: the only station-channel rows that are valid for this task.
- `/root/data/precomputed_phase_picks.csv`: upstream phase picks that already contain a backshift estimate to event origin time.

Each row in `precomputed_phase_picks.csv` has:

- `trace_id`: the waveform trace to use, such as `CI.CCC..HHZ`
- `phase`: `P` or `S`
- `arrival_sample`: sample index counted from the start of the referenced trace
- `origin_backshift_s`: seconds to subtract from the absolute arrival time to recover one origin-time proposal
- `score`: a pick quality score you may ignore

Your task is to build a unique earthquake time table for the Ridgecrest window.

Required workflow:

1. Read the MiniSEED file and recover each trace's absolute `starttime`, `sampling_rate`, and channel identifiers from waveform metadata.
2. Convert every valid pick into an absolute origin-time proposal using:
   `origin_time = trace_starttime + arrival_sample / sampling_rate - origin_backshift_s`
3. Keep only picks whose `(network, station, channel)` exist in both the waveform file and `stations_subset.csv`.
4. Merge nearby origin-time proposals into unique earthquakes. In this dataset, proposals within `1.2` seconds of each other belong to the same event.
5. For each merged event, count the number of distinct supporting stations and the total number of supporting picks.
6. Keep only merged events with at least `3` distinct stations and at least `4` picks.

Write `/root/associated_events.csv` sorted by time ascending. It must contain these columns:

- `time`: event origin time in ISO format without timezone suffix
- `station_count`: number of distinct stations contributing to the merged event
- `phase_count`: number of picks contributing to the merged event

Evaluation:

- Only the time window covered by the provided data is relevant.
- Your `time` values will be matched to a reference catalog with a tolerance of `1.5` seconds.
- To pass, your output must achieve `precision >= 0.90` and `recall >= 0.90`.
