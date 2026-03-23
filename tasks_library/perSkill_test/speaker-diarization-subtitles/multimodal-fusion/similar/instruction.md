A repaired speaker timeline is needed from precomputed meeting logs.

Inputs:

- `/root/data/segment_draft.json`
- `/root/data/visual_observations.json`
- `/root/data/audio_cluster_map.json`
- `/root/data/session_meta.json`

Create these files:

- `/root/diarization.rttm`
- `/root/subtitles.ass`
- `/root/report.json`

Rules:

1. For each segment, use the midpoint of `[start, end]` to align it to the nearest visual observation within `0.75` seconds.
2. If that observation contains exactly one `lip_tracks` entry, use the mapped speaker from `session_meta.json`.
3. Otherwise, use the fallback speaker from `audio_cluster_map.json`.
4. Keep the original segment boundaries and ordering. Do not merge or split segments.
5. Write RTTM lines as `SPEAKER input 1 <start> <duration> <NA> <NA> <speaker> <NA> <NA>` with `speaker` in the `spkNN` format.
6. Write ASS dialogue lines in order, using `SPEAKER_NN: <transcript>` as the subtitle text.
7. `report.json` must contain:
   - `num_speakers_pred`
   - `total_speech_time_sec`
   - `audio_duration_sec`
   - `steps_completed`
   - `commands_used`
   - `libraries_used`
   - `tools_used`
   - `visual_overrides`
   - `audio_fallbacks`
   - `notes`
8. Round all seconds in `report.json` to 2 decimals.
