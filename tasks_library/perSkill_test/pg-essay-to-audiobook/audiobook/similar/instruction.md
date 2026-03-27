Create one audiobook WAV from two local essay pages.

Input files:
- `/root/data/do-things.html`
- `/root/data/founder-mode.html`

Output files:
1. `/root/similar_audiobook.wav`
2. `/root/similar_manifest.json`

Requirements:
1. Process chapters in this fixed order:
   - `Do Things that Don't Scale`
   - `Founder Mode`
2. Extract readable body text from each HTML file:
   - Remove `script` and `style` blocks.
   - Remove all HTML tags.
   - Normalize whitespace to single spaces.
3. Clean extracted text for narration:
   - Remove URLs (`http://` or `https://...`).
   - Remove bracketed footnote markers like `[1]`, `[23]`.
   - Keep punctuation needed for sentence splitting.
4. For each chapter, prepend `Chapter: <title>. ` to the cleaned body.
5. Chunk each chapter into segments with max length 220 characters, splitting only on sentence boundaries (`.`, `!`, `?`).
6. Synthesize each chunk into WAV using `/root/tools/offline_tts.py`.
7. Concatenate chunk audio in chapter order into `/root/similar_audiobook.wav`.
8. Determine provider label with fallback logic:
   - `elevenlabs` if `ELEVENLABS_API_KEY` exists
   - else `openai` if `OPENAI_API_KEY` exists
   - else `gtts`
9. Write `/root/similar_manifest.json` with keys:
   - `provider` (string)
   - `chapter_titles` (array)
   - `chapter_count` (int)
   - `total_chunks` (int)
   - `total_clean_chars` (int)

Do not read files from `/tests`.
