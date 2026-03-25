A scene-by-scene speaker presence summary is needed for an edited studio clip.

Inputs:

- `/root/data/scene_boundaries.json`
- `/root/data/utterance_log.json`
- `/root/data/visual_frames.json`
- `/root/data/speaker_directory.json`

Create `/root/transfer3_scene_presence_summary.json`.

Rules:

1. For each utterance, align its midpoint to the nearest visual frame within `0.75` seconds.
2. If that frame contains exactly one `lip_tracks` entry, use the mapped speaker for that utterance. Otherwise, use the fallback speaker from `speaker_directory.json`.
3. Group utterances into scenes by midpoint, using the inclusive `[start, end]` scene ranges from `scene_boundaries.json`.
4. For each scene, output an object with:
   - `scene_id`
   - `dominant_speaker`
   - `total_speech_sec`
   - `visual_support_ratio`
   - `supporting_segments`
   - `offscreen_segments`
5. `dominant_speaker` is the speaker with the largest total assigned duration in that scene.
6. `visual_support_ratio` is `visual_supported_duration / total_speech_duration`, rounded to 2 decimals.
7. `supporting_segments` contains the utterance IDs assigned to the dominant speaker, in input order.
8. `offscreen_segments` contains the subset of `supporting_segments` whose aligned frame does not show the dominant speaker in `visible_tracks`.
9. Preserve the scene order from `scene_boundaries.json`.
