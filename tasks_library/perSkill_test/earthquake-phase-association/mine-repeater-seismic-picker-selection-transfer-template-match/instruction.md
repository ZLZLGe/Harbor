You are supporting an underground microseismic monitoring team that is tracking repeating events around an active stope.

Inputs are in `/root/mine_inputs/`:

- `continuous_energy_trace.csv`: a simple text export of short-window signal energy from the array.
- `array_layout.csv`: one row per underground sensor.
- `template_inventory.csv`: the existing high-quality repeater template library.
- `shift_brief.md`: operational context for this shift.
- `review_summary.csv`: analyst-checked windows summarizing how each candidate family behaved.
- `blast_windows.csv`: scheduled production blast intervals that must not appear in the final event list.
- `candidate_repeater_sta_lta.csv`
- `candidate_repeater_deep_learning.csv`
- `candidate_repeater_template_matching.csv`

Your task is to choose the most appropriate candidate detection family for this monitoring problem and write the final detections to `/root/mine_repeater_events.csv`.

Rules:

1. Base your choice on the operational brief, the existing template library, and the reviewed windows. The goal is a sensitive final list of repeating microseismic events for a template-rich mining panel, not broad discovery of unknown source types.
2. Do not rerun detection from scratch. Select one of the three provided candidate files.
3. Remove every detection whose `time` falls inside any interval in `blast_windows.csv`, including the start and end timestamps.
4. On the remaining rows, collapse duplicate detections only when both of these are true:
   - they share the same `repeater_family`
   - their times are within 1.5 seconds of each other
5. When collapsing duplicates, keep the row with higher `correlation_peak`. If that is tied, keep the row with higher `sensor_count`. If that is still tied, keep the earlier `time`.
6. Sort the final detections by `time` ascending.
7. Write `/root/mine_repeater_events.csv` with exactly these columns:
   - `time`
   - `repeater_family`
   - `template_id`
   - `sensor_count`
   - `correlation_peak`
   - `method_family`
8. Set `method_family` to one of `sta_lta`, `deep_learning`, or `template_matching`, matching the candidate family you selected.

No relocation, magnitude estimation, or extra columns are required.
