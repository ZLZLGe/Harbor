A cue alignment manifest is needed for a short lab panel recording.

Inputs:

- `/root/data/alignment_segments.csv`
- `/root/data/camera_events.json`
- `/root/data/speaker_catalog.json`

Create `/root/transfer1_alignment_manifest.json` as a JSON array.

Rules:

1. For each segment, use the midpoint of `[start, end]` to find the nearest camera event within `0.8` seconds.
2. If that event has exactly one `lip_tracks` entry, assign the speaker mapped from that track and set `evidence` to `visual-lip`.
3. Otherwise, if that event has exactly one `visible_tracks` entry, assign that visible speaker and set `evidence` to `single-visible`.
4. Otherwise, use the fallback speaker for the segment's `audio_cluster` and set `evidence` to `audio-default`.
5. Output one object per segment with these fields:
   - `segment_id`
   - `start`
   - `end`
   - `assigned_speaker`
   - `on_screen`
   - `evidence`
   - `subtitle_text`
6. `on_screen` is true when the assigned speaker is visible in the chosen event, otherwise false.
7. Preserve the input order and round `start` and `end` to 2 decimals.
