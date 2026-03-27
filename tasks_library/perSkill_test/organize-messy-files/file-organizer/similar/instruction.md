Organize the mixed files in `/root/inbox` into exactly these subject folders under `/root/library`:

- `LLM`
- `trapped_ion_and_qc`
- `black_hole`
- `DNA`
- `music_history`

Ground truth mapping is provided in `/root/data/expected_layout.json`.

Requirements:
- move every listed file into its required subject folder
- do not rename any file
- after sorting, no files from the task dataset may remain in `/root/inbox`
- create `/root/similar_sort_report.json`

The report must contain:
- `total_files`
- `moved_files`
- `folders` (object with per-folder counts)
