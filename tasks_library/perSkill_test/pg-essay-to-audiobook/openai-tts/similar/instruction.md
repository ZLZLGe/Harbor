Create a single narrated audio program from the chapter excerpts in `/root/data/essay_fragments.json`.

Input:
- `/root/data/essay_fragments.json`
- `/root/data/task_config.json`

Save:
- `/root/similar_founder_notes.mp3`
- `/root/similar_founder_notes_manifest.json`

Requirements:
- preserve chapter order from the input file
- include a short spoken chapter header before each chapter body
- output manifest must include `chapters`, `voice`, `model`, and `total_duration_sec`
- each item in `chapters` must include `chapter_id`, `title`, `duration_sec`, and `char_count`
