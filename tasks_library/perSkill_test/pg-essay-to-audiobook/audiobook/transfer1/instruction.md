Create a chaptered WAV briefing digest from local markdown packets.

Input files:
- `/root/data/playlist_order.json`
- `/root/data/briefing_alpha.md`
- `/root/data/briefing_beta.md`
- `/root/data/briefing_gamma.md`

Output files:
1. `/root/transfer1_city_briefing.wav`
2. `/root/transfer1_chapter_stats.csv`

Requirements:
1. Read chapters in the exact order declared in `playlist_order.json`.
2. For each markdown file:
   - Remove fenced code blocks.
   - Remove markdown headings (`# ...`).
   - Remove leading list markers (`- ` and `* `).
   - Remove URLs.
   - Normalize whitespace to single spaces.
3. Build chapter narration as: `Briefing: <title>. <cleaned_text>`.
4. Chunk each chapter narration into max 180 characters, splitting only at sentence boundaries (`.`, `!`, `?`).
5. Synthesize each chunk with `/root/tools/offline_tts.py` and concatenate all chunks into `/root/transfer1_city_briefing.wav`.
6. Write `/root/transfer1_chapter_stats.csv` with header:
   `chapter_title,char_count,chunk_count`
   - `char_count` counts cleaned chapter text only (without the intro prefix).
   - One row per chapter, in playlist order.

Do not read files from `/tests`.
