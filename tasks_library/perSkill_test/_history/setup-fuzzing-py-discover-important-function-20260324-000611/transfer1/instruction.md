Three Python packages are staged under `/root/repos` for a release-readiness review.

Inspect the repositories and create `/root/transfer1_regression_queue.csv`.

Use this exact header:
`repo,target,test_signal,missing_case,priority`

Requirements:
- include exactly one row for each repository: `mailroompkg`, `quotaflags`, `slugrender`
- sort rows by `repo`
- `target` must be the single most important fully qualified function to probe next
- `test_signal` must be the most relevant existing test file
- `missing_case` must be a short phrase describing the highest-value edge case that is not already covered
- `priority` must be `P1`
