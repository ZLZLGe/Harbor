Normalize a local TTS queue into deterministic request objects.

Input file:
- `/root/data/raw_queue.jsonl`

Output files:
1. `/root/transfer2_queue_normalized.json`
2. `/root/transfer2_rejected_ids.txt`

Requirements:
1. Read one JSON object per line from `raw_queue.jsonl`.
2. Clean `text` for each row:
   - Remove URLs.
   - Remove bracketed footnote markers like `[3]`.
   - Normalize whitespace.
3. Reject rows when:
   - `enabled` is not `true`, or
   - cleaned text is empty.
4. For accepted rows:
   - `voice_id` must be one of:
     - `21m00Tcm4TlvDq8ikWAM`
     - `EXAVITQu4vr4xnSDxMaL`
     - `ErXwobaYiN019PkySvjV`
     - `TxGEqnHWrfWFTfGW9XjX`
   - if invalid/missing, fall back to `21m00Tcm4TlvDq8ikWAM`.
5. Chunk cleaned text by sentence boundaries (`.`, `!`, `?`) with max 1500 chars per chunk.
   - If one sentence exceeds 1500 chars, split it into hard 1500-char pieces.
6. Clamp `stability` and `similarity_boost` to range `[0.0, 1.0]`.
   - If missing or non-numeric, use `0.5`.
7. Emit `/root/transfer2_queue_normalized.json` with keys:
   - `requests` (array)
   - `meta` (object with `source_jobs`, `accepted_jobs`, `rejected_jobs`)
8. Each request item must contain:
   - `request_id` (`<id>-<chunk_index>`)
   - `url`
   - `headers` with `xi-api-key` and `Content-Type`
   - `body` with `text`, `model_id`, `voice_settings`
   - `body.model_id` must be `eleven_turbo_v2_5`
9. Write rejected job IDs to `/root/transfer2_rejected_ids.txt`, one per line, sorted ascending.

Do not read files from `/tests`.
