Generate a narrated casefile audio from structured incident fragments.

Input files:
- `/root/data/casefile_fragments.csv`
- `/root/data/phase_order.json`

Required outputs:
1. `/root/casefile_narration.mp3`
2. `/root/casefile_segments.json`

Rules:
1. Read phase order from `phase_order.json` key `order`.
2. Parse CSV rows with columns `case_id`, `phase`, `note`.
3. Sort rows by:
   - `case_id` ascending,
   - then phase rank from configured order,
   - then source row order.
4. Build narration in this pattern:
   - start each case with `Case <case_id> summary.`
   - then for each row: `Case <case_id>, <phase> phase: <note>.`
5. Normalize whitespace in notes.
6. Chunk narration at sentence boundaries with max 190 characters.
7. Synthesize chunks and concatenate to `/root/casefile_narration.mp3`.
8. Write `/root/casefile_segments.json` containing keys:
   - `provider`
   - `case_ids`
   - `phase_order`
   - `segment_count`
   - `chars_per_case`
   - `total_chunks`
   - `gtts_chunk_count`

If online TTS is unavailable, use a local fallback and still complete the task.
Do not read from `/tests`.
