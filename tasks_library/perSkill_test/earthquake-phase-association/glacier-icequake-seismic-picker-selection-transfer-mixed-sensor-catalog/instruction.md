You are given one hour of continuous glacier-seismic monitoring data from a sparse mixed-sensor network near an active icefall.

Input files:
- Continuous waveform archive: `/root/data/icefield_continuous.mseed`
- Channel metadata: `/root/data/mixed_sensor_channels.csv`
- Field memo describing the deployment constraints: `/root/data/field_memo.txt`
- Candidate event table assembled from several automatic approach families: `/root/data/candidate_icequakes.csv`
- Approach scorecard summarizing expected tradeoffs: `/root/data/approach_scorecard.csv`
- Scheduled maintenance and calibration windows: `/root/data/maintenance_windows.csv`

Each row of `mixed_sensor_channels.csv` represents one recorded channel and includes:
1. `network`, `station`, `location`, `channel`
2. `longitude`, `latitude`
3. `elevation_m`
4. `response`

The channel families are mixed during this hour. In this deployment, the operators treat `BH*` and `HH*` as the higher-gain seismic channels and `HN*` as strong-motion channels.

Each row of `candidate_icequakes.csv` represents one automatically proposed event and includes:
1. `time`
2. `approach_family`
3. `support_stations`
4. `sensor_class_count`, `sensor_types`
5. `median_pick_probability`, `network_coherence`
6. `template_support`, `sta_lta_ratio`
7. `calibration_flag`
8. `comment`

Your goal is to produce a candidate icequake schedule for analyst review. This is not a final glacier event catalog: the priority is to keep plausible mixed-sensor icequake candidates from the most suitable automatic approach while excluding calibration periods and obvious single-sensor noise.

Requirements:
1. Read the field memo and choose one automatic picking or detection approach family that best matches this glacier-monitoring setup.
2. Use `candidate_icequakes.csv`, `approach_scorecard.csv`, and `maintenance_windows.csv` to select candidate icequakes for analyst review.
3. Write a short plain-text rationale for the chosen approach to `/root/icequake_method.txt`.
4. Write the accepted candidate schedule to `/root/icequake_candidates.csv`.

Output requirements for `/root/icequake_candidates.csv`:
- It must be a CSV file.
- Each row must represent one candidate icequake.
- It must contain a `time` column in ISO format without timezone.
- It must contain `approach_family`, `support_stations`, `sensor_types`, and `median_pick_probability` columns.
- It should also keep enough metadata for a reviewer to understand why each candidate was accepted.
- It must be sorted by time in ascending order.
- It must not include candidates that fall inside the listed maintenance windows.

Evaluation:
- We will check that the chosen approach matches the glacier field constraints.
- We will compare your candidate times against a reviewed reference schedule with a small timing tolerance.
- We will also check that your output preserves mixed-sensor support and excludes maintenance-window artifacts.
