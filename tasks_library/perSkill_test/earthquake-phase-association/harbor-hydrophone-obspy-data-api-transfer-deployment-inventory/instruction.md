You are given segmented MiniSEED packets in `/root/data/packets/` and a hydrophone deployment table in `/root/data/deployments.csv`.

Each row of `deployments.csv` represents one planned channel deployment and contains:
1. `network`, `station`, `location`, `channel`
2. `latitude`, `longitude`, `elevation_m`
3. `depth_m`, `azimuth_deg`, `dip_deg`
4. `site_name`, `mooring_id`
5. `planned_start`, `planned_end` in ISO format without timezone

Build a StationXML inventory at `/root/hydrophone_inventory.xml` using the following rules:

1. Read every MiniSEED packet in `/root/data/packets/` and treat them as one waveform archive.
2. Only channels declared in `deployments.csv` are eligible for the inventory.
3. For each declared channel, inspect all matching waveform traces:
   - if there is no overlap between the planned deployment window and the waveform availability, omit that channel entirely
   - otherwise set the channel start time to the later of `planned_start` and the earliest waveform sample time
   - set the channel end time to the earlier of `planned_end` and the latest waveform sample time
   - set the channel sample rate from the matching waveform headers
4. Copy `latitude`, `longitude`, `elevation_m`, `depth_m`, `azimuth_deg`, and `dip_deg` from the deployment row onto the channel metadata.
5. Group channels into StationXML `Network` / `Station` / `Channel` hierarchy by their declared IDs.
6. For each station:
   - include only stations that still have at least one channel after rule 3
   - use the repeated station coordinates/elevation from the CSV
   - set the station site name from `site_name`
   - set the station start and end times to the min/max of its included channels
7. For each network, set its start and end times to the min/max of its included stations.
8. Keep the inventory deterministic by sorting networks, stations, and channels by their IDs before writing.
9. You do not need to synthesize any instrument response stages.

Only `/root/hydrophone_inventory.xml` will be graded.
