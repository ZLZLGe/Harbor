Build a deterministic dubbing cast plan from local segment rows.

Input file:
- `/root/data/dubbing_segments.csv`

Output files:
1. `/root/transfer1_voice_plan.csv`
2. `/root/transfer1_casting_notes.json`

Requirements:
1. Read CSV rows and keep only rows where `publish` equals `yes` (case-insensitive).
2. Sort kept rows by numeric `segment_id` ascending.
3. Clean each row text:
   - Remove URLs.
   - Remove bracketed footnote markers like `[2]`.
   - Normalize whitespace.
4. Voice mapping by `persona`:
   - `calm_female` -> `21m00Tcm4TlvDq8ikWAM`
   - `soft_female` -> `EXAVITQu4vr4xnSDxMaL`
   - `warm_male` -> `ErXwobaYiN019PkySvjV`
   - `deep_male` -> `TxGEqnHWrfWFTfGW9XjX`
5. Chunk cleaned text by sentence boundaries (`.`, `!`, `?`) with max 1000 chars per chunk.
   - If one sentence exceeds 1000 chars, split it into hard 1000-char pieces.
6. Write `/root/transfer1_voice_plan.csv` with header:
   - `segment_id,persona,voice_id,char_count,chunk_count,model_id`
   - `model_id` must be `eleven_turbo_v2_5`.
7. Write `/root/transfer1_casting_notes.json` with keys:
   - `total_segments`
   - `total_chunks`
   - `persona_counts` (object)
   - `voice_ids_used` (sorted array)

Do not read files from `/tests`.
