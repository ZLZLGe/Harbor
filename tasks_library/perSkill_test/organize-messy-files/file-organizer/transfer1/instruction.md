You received a mixed drop folder at `/root/media_drop`.

Use `/root/data/organization_plan.json` and reorganize files with these rules:
- files listed under `duplicate_groups` belong to one duplicate set
- in each duplicate set, keep the lexicographically smallest filename as the canonical copy
- move canonical files to `/root/organized/<category>/`
- move non-canonical files to `/root/organized/duplicates/<group>/`
- files listed under `unique_files` should be moved to `/root/organized/<category>/`

Do not rename files.

Create `/root/transfer1_keep_decisions.csv` with columns:
- `file`
- `group`
- `decision` (`keep`, `duplicate`, or `unique`)
- `target`

Every input file from `/root/media_drop` must appear exactly once in the CSV.
