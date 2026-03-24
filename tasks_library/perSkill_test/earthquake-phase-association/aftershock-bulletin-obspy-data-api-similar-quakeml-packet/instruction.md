You are given three continuous MiniSEED packets in `/root/data/segments/`, a station-channel manifest in `/root/data/station_channels.csv`, and a candidate aftershock bulletin in `/root/data/candidate_events.csv`.

Each row of `station_channels.csv` represents one declared channel and includes:
1. `network`, `station`, `location`, `channel`
2. `longitude`, `latitude`, `elevation_m`
3. `response`

Each row of `candidate_events.csv` contains:
1. `candidate_id`
2. `origin_time` in ISO format without timezone
3. `analyst_note`

Build a QuakeML catalog at `/root/aftershock_catalog.xml` using the following rules:

1. Read all MiniSEED packets and treat them as one continuous archive.
2. For every candidate event, inspect the fixed waveform window from `origin_time - 12 s` to `origin_time + 18 s`.
3. A station supports a candidate if at least one complete 3-component bundle covers the full window:
   - either `HHE`, `HHN`, `HHZ`
   - or `HNE`, `HNN`, `HNZ`
4. Ignore single-component channels such as `EHZ` when deciding support.
5. Drop any candidate with fewer than `11` supporting stations.
6. For each retained candidate, create one QuakeML event containing:
   - an origin whose time is exactly the candidate `origin_time`
   - the support count stored in `Origin.quality.used_station_count`
7. Sort events by origin time before writing the catalog.

Only `/root/aftershock_catalog.xml` will be graded.
