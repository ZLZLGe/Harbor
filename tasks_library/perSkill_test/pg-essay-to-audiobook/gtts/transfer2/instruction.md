Create an audio recap from a queue of call snippets.

Input files:
- `/root/data/call_snippets.jsonl`
- `/root/data/severity_order.json`

Required outputs:
1. `/root/call_recap.mp3`
2. `/root/call_recap_report.json`

Rules:
1. Read severity order from `severity_order.json` key `order`.
2. Parse every JSONL entry with fields `case_id`, `speaker`, `severity`, `text`.
3. Order entries by:
   - severity according to configured order,
   - then original appearance order in the JSONL file.
4. Build narration text as:
   - one section opener per severity: `Priority <severity> updates.`
   - then one sentence per entry: `<speaker> from <case_id> reports: <text>.`
5. Chunk narration at sentence boundaries with max 170 characters.
6. Synthesize and concatenate all chunks into `/root/call_recap.mp3`.
7. Write `/root/call_recap_report.json` with keys:
   - `provider`
   - `severity_order`
   - `item_count`
   - `unique_cases`
   - `chars_by_severity`
   - `total_chunks`
   - `gtts_chunk_count`

If online TTS is unavailable, use a local fallback and still produce valid output.
Do not read from `/tests`.
