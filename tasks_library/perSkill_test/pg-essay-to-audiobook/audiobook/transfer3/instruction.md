Build one sectioned casefile narration WAV from CSV fragments.

Input file:
- `/root/data/casefile_fragments.csv`

Output files:
1. `/root/transfer3_casefile_audio.wav`
2. `/root/transfer3_cues.txt`

Requirements:
1. Read CSV rows with columns: `section,rank,text`.
2. Sort rows by:
   - `section` ascending (lexicographic)
   - `rank` ascending (numeric)
3. Clean each row text:
   - Remove URLs.
   - Remove bracketed footnote markers like `[7]`.
   - Normalize whitespace.
4. Deduplicate globally by cleaned text (case-insensitive): keep only the first occurrence in sorted order.
5. Build narration text:
   - When a section appears for the first kept row, insert `Section <section>.`
   - Then insert `<section>: <cleaned_text>.` for each kept row.
6. Chunk the narration into max 200 characters using sentence boundaries (`.`, `!`, `?`).
7. Synthesize chunks with `/root/tools/offline_tts.py` and concatenate into `/root/transfer3_casefile_audio.wav`.
8. Write `/root/transfer3_cues.txt` with one line per kept row:
   `<index>|<section>|<chars>`
   - `index` is 1-based in kept-row order.
   - `chars` is the character count of cleaned text.

Do not read files from `/tests`.
