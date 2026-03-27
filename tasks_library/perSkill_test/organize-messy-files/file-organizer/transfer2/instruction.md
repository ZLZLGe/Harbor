A legacy project dump is stored in `/root/project_dump`.

Use `/root/data/archive_spec.json` to place each file into this structure:
- `/root/projects_sorted/active/<project>/...`
- `/root/projects_sorted/archive/<project>/...`

Rules:
- each file has one destination defined by `bucket` and `project`
- move every listed file
- do not rename files
- after processing, `/root/project_dump` must have none of the listed files left

Create `/root/transfer2_archive_plan.json` with:
- `total_files`
- `bucket_counts` (counts per `active` / `archive`)
- `project_counts` (counts per project)
- `destinations` (sorted list of absolute destination paths)
