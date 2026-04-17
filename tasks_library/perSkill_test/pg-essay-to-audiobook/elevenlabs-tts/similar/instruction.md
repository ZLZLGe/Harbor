Create a deterministic ElevenLabs request package from local chapter packets.

Input files:
- `/root/data/essay_packets.json`
- `/root/data/voice_aliases.json`

Output files:
1. `/root/similar_elevenlabs_requests.jsonl`
2. `/root/similar_concat_manifest.txt`

Requirements:
1. Read chapters from `essay_packets.json` in listed order.
2. For each chapter text:
   - Remove URLs (`http://` or `https://...`).
   - Remove bracketed footnote markers like `[1]`.
   - Normalize whitespace to single spaces.
3. Build narration text as: `Chapter: <title>. <cleaned_text>`.
4. Chunk narration by sentence boundaries (`.`, `!`, `?`) with max 1200 chars per chunk.
   - If one sentence still exceeds 1200 chars, split it into hard 1200-char pieces.
5. Resolve `voice_hint` using `voice_aliases.json` and emit one JSON object per chunk in `/root/similar_elevenlabs_requests.jsonl` with keys:
   - `chapter_title`
   - `chunk_index` (1-based within chapter)
   - `voice_id`
   - `url` (`https://api.elevenlabs.io/v1/text-to-speech/<voice_id>`)
   - `headers` containing `xi-api-key` and `Content-Type`
   - `body` containing `text`, `model_id`, `voice_settings`
6. `body.model_id` must be `eleven_turbo_v2_5`.
7. `body.voice_settings` must be exactly:
   - `stability = 0.5`
   - `similarity_boost = 0.75`
8. Write `/root/similar_concat_manifest.txt` with one line per chunk in global order:
   - `file 'chapterXX_chunkYYY.mp3'`

Do not read files from `/tests`.
