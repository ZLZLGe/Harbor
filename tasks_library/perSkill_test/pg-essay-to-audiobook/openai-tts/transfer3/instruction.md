Create one narrated digest from `/root/data/release_notes.md`.

Input:
- `/root/data/release_notes.md`
- `/root/data/task_config.json`

Save:
- `/root/transfer3_release_digest.aac`
- `/root/transfer3_release_markers.csv`

Requirements:
- treat each `##` heading as one section in order
- include section heading in the spoken content for each section
- marker CSV columns must be exactly: `section,start_sec,end_sec,word_count`
- marker rows must be in the same order as sections in the source document
