You are given a precomputed volcano swarm pick table at `/root/data/swarm_picks.csv` and summit-network station metadata at `/root/data/volcano_stations.csv`.

The pick table contains phase arrivals from a short unrest window near a volcano. Each row has:
1. `id`: station identifier
2. `timestamp`: phase arrival time in ISO format without timezone
3. `prob`: pick confidence
4. `type`: phase label, either `p` or `s`

The station table has these columns:
1. `id`: station identifier matching the pick table
2. `network`, `station`: station codes
3. `longitude`, `latitude`: station location in degrees
4. `elevation_m`: station elevation in meters above sea level

Assume a uniform velocity model with `vp = 5.4 km/s` and `vs = vp / 1.78`.

Associate the picks into unique volcano swarm events and estimate each event's origin time and hypocenter.

Write the final event layer to `/root/volcano_swarm_events.geojson` as a GeoJSON `FeatureCollection`.

Requirements for the GeoJSON output:
1. Each event must be a `Feature` with `Point` geometry in `[longitude, latitude]` order.
2. Each feature's `properties` must include at least: `time`, `depth_km`, `num_picks`, `num_p_picks`, `num_s_picks`.
3. `time` must be in ISO format without timezone.
4. The file should contain one feature per associated event.

You may include additional event-level properties if they help downstream monitoring.
