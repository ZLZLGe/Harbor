You are helping a field team build a first-pass aftershock catalog for a temporary broadband deployment.

Inputs are in `/root/bootstrap_data/`:

- `continuous_excerpt.csv`: a simple text export of continuous vertical waveform amplitudes for the deployment interval.
- `stations.csv`: one row per temporary broadband station.
- `deployment_notes.md`: field constraints and what the team needs from this first-pass catalog.
- `manual_review_windows.csv`: a few short windows that were already checked by a human analyst.
- `candidate_catalog_sta_lta.csv`
- `candidate_catalog_deep_learning.csv`
- `candidate_catalog_template_matching.csv`

Your task is to choose the most appropriate candidate catalog for this deployment and write the final event list to `/root/bootstrap_events.csv`.

Rules:

1. Base your choice on the deployment constraints and the reviewed windows. The goal is a practical automatic local catalog for a temporary broadband network during an active aftershock sequence.
2. Do not re-run phase picking from scratch. The point is to select the right candidate family from the three provided options.
3. After choosing one candidate file, collapse duplicate detections that are within 4 seconds of each other.
4. When collapsing duplicates, keep the row with larger `supporting_stations`. If that is tied, keep the row with larger `mean_pick_score`. If that is still tied, keep the earlier `time`.
5. Keep every remaining event from the chosen candidate, including events outside the manually reviewed windows.
6. Sort the final catalog by `time` ascending.
7. Write `/root/bootstrap_events.csv` with exactly these columns:
   - `time`
   - `supporting_stations`
   - `mean_pick_score`
   - `method_family`
8. Set `method_family` to one of `sta_lta`, `deep_learning`, or `template_matching`, matching the candidate family you selected.

No relocation, magnitude estimation, or extra columns are required.
