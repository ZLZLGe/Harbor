A manual review queue is needed for a short broadcast clip.

Inputs:

- `/root/data/draft_turns.json`
- `/root/data/visual_checks.csv`
- `/root/data/label_defaults.json`

Create `/root/transfer2_review_queue.csv`.

Rules:

1. For each segment, align its midpoint to the nearest visual check within `0.7` seconds.
2. Use the fallback speaker name from `label_defaults.json` as the segment's `audio_speaker`.
3. Add a review row when one of these conditions is met:
   - `speaker_conflict`: exactly one lip track is present and it maps to a different speaker than the audio speaker.
   - `crowded_frame`: at least 3 visible tracks are present and there are no lip tracks.
   - `offscreen_or_missing_camera`: no visible tracks are present.
4. Output only the flagged rows, sorted by `start` ascending.
5. The CSV columns must be:
   - `segment_id`
   - `start`
   - `end`
   - `audio_speaker`
   - `review_reason`
   - `recommended_action`
   - `suggested_speaker`
6. For `speaker_conflict`, set `recommended_action` to `relabel_to_visual_speaker` and `suggested_speaker` to the visual speaker name.
7. For `crowded_frame`, set `recommended_action` to `manual_visual_review` and leave `suggested_speaker` empty.
8. For `offscreen_or_missing_camera`, set `recommended_action` to `verify_audio_only_segment` and leave `suggested_speaker` empty.
9. Round `start` and `end` to 2 decimals.
