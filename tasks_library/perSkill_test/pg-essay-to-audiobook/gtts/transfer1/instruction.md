Prepare an audio digest from three local crisis briefings.

Input files:
- `/root/data/briefing_alpha.md`
- `/root/data/briefing_beta.md`
- `/root/data/briefing_gamma.md`
- `/root/data/playlist_order.json`

Required outputs:
1. `/root/briefing_digest.mp3`
2. `/root/briefing_index.json`

Rules:
1. Read briefing order from `playlist_order.json` key `order`.
2. For each briefing:
   - remove markdown heading markers (`#`, `##`, ...),
   - remove list bullet markers (`-`),
   - collapse whitespace,
   - remove URLs and bracketed numeric references like `[7]`.
3. Prefix each briefing body with `Briefing: <title>. ` where title is the first heading text.
4. Chunk narration text at sentence boundaries with max 210 characters per chunk.
5. Synthesize all chunks and concatenate in playlist order into `/root/briefing_digest.mp3`.
6. Write `/root/briefing_index.json` with keys:
   - `provider`
   - `ordered_ids`
   - `ordered_titles`
   - `chunk_counts`
   - `total_chunks`
   - `total_input_chars`
   - `gtts_chunk_count`

If online TTS is unavailable, use a local fallback and still complete the task.
Do not read from `/tests`.
