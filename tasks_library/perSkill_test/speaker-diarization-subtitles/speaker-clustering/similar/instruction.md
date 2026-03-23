A short operations briefing has already been segmented into speech windows. The segment list is available at:

- `/root/data/briefing_segments.json`

Each entry includes:

- `segment_id`
- `start_sec`
- `end_sec`
- `signature` (a numeric voice-signature vector)

Assign consistent speaker labels across all segments, then merge back-to-back windows from the same speaker when the silence gap is `<= 0.08` seconds.

Write these outputs:

1. `/root/output/similar_diarization.rttm`
   - use `spk00`, `spk01`, ... speaker labels
   - write one RTTM line per merged turn
   - use `briefing` as the RTTM file id

2. `/root/output/similar_cluster_report.json`
   - include `speaker_count`
   - include `segment_count`
   - include `merged_turn_count`
   - include `speaker_durations_sec`

Keep the turn order chronological.
