Create a single chaptered audiobook MP3 from two local essay snapshots.

Input files:
- `/root/data/do-things.html`
- `/root/data/founder-mode.html`

Required outputs:
1. `/root/audiobook.mp3`
2. `/root/audiobook_manifest.json`

Rules:
1. Keep chapter order exactly:
   - `Do Things that Don't Scale`
   - `Founder Mode`
2. Parse each HTML file by:
   - removing `script` and `style` blocks,
   - stripping all HTML tags,
   - collapsing whitespace to single spaces.
3. Clean narration text by removing URLs and bracketed numeric references like `[12]`.
4. Prefix each chapter with `Chapter: <title>. ` before chunking.
5. Chunk text with max 260 characters, splitting on sentence boundaries (`.`, `!`, `?`).
6. Generate audio for every chunk and concatenate in chapter order to `/root/audiobook.mp3`.
7. Write `/root/audiobook_manifest.json` containing keys:
   - `provider`
   - `chapter_titles`
   - `chapter_count`
   - `total_chunks`
   - `total_clean_chars`
   - `gtts_chunk_count`

If online TTS is unavailable, use a local fallback and still produce valid outputs.
Do not read from `/tests`.
