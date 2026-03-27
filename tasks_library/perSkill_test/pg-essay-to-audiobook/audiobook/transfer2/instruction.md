Create one training-call digest WAV from local JSONL snippets.

Input file:
- `/root/data/call_snippets.jsonl`

Output files:
1. `/root/transfer2_training_digest.wav`
2. `/root/transfer2_digest.json`

Requirements:
1. Read JSON objects from `call_snippets.jsonl`.
2. Keep only rows where:
   - `publish` is `true`
   - `priority >= 2`
3. Sort kept rows by `session_id` ascending. If ties occur, sort by `speaker` ascending.
4. Clean each kept row text:
   - Remove URLs.
   - Remove bracketed footnote markers like `[3]`.
   - Normalize whitespace.
5. Convert each kept row into one narration sentence:
   `Segment <session_id> - <speaker>: <cleaned_text>.`
6. Concatenate all narration sentences in order, then chunk into max 160 characters using sentence boundaries (`.`, `!`, `?`).
7. Synthesize chunk WAVs with `/root/tools/offline_tts.py`, then concatenate into `/root/transfer2_training_digest.wav`.
8. Write `/root/transfer2_digest.json` with keys:
   - `included_session_ids` (sorted unique int array)
   - `segment_count` (int)
   - `chunk_count` (int)
   - `total_chars` (int, characters of concatenated narration text before chunking)

Do not read files from `/tests`.
