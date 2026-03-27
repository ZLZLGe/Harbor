You are preparing fuzzing intake notes for three Python libraries stored under `/root/repos`.

Inspect each repository and create `/root/similar_fuzz_target_plan.json` as a JSON array with one object per repository.

Each object must contain:
- `repo`
- `important_file`
- `functions`
- `test_signal`
- `harness_hint`

Requirements:
- include exactly these repositories: `badgecodec`, `ledgerparse`, `sensorrules`
- sort the array by `repo`
- `functions` must list the two highest-value candidate functions for that repository, using fully qualified names
- `important_file` must be a repository-relative path
- `test_signal` must name the most relevant test file that already exercises the selected area
- `harness_hint` must be a short sentence describing what malformed or boundary-shaped input the future fuzz driver should mutate
