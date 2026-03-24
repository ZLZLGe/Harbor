You are given one short continuous seismic record at `/root/data/continuous_waveforms.csv` and two high-quality seed-event templates listed in `/root/data/seed_catalog.csv`.

Data layout:
- `continuous_waveforms.csv` contains 180 seconds of 20 Hz waveform samples. The `time` column is the sample timestamp in ISO format without timezone. Every other column is one trace named as `<station>_<channel>`, for example `RV01_HHZ`.
- `seed_catalog.csv` lists the provided seed events. Each row includes a `family_id`, the corresponding `template_file`, and the original `seed_time`.
- Each template file in `/root/data/` has the same trace columns as the continuous record, plus `relative_time_s` for the sample offset inside the template window.

Your goal is to find additional repeating microearthquakes in the continuous record that match the provided seed families, including weaker repeats, and report only the newly detected events.

Write your result to `/root/repeater_detections.csv`.

The output must contain at least these columns:
- `detection_time`
- `matched_family`
- `score`

Requirements:
1. `detection_time` must be in ISO format without timezone.
2. `matched_family` should identify which seed family best matches the detection.
3. `score` must be numeric.
4. Report each repeated event once and sort rows by `detection_time`.
5. Do not include the original seed events from `seed_catalog.csv` in the output.

You may include extra columns if helpful, but the required columns above must be present.
