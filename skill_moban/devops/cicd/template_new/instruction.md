You are triaging a flaky Playwright CI failure that appeared on `main` after a release PR was merged. The repository under test is in `/app/repo`, and the exported CI logs are in `/app/ci-logs`.

Input data is in:

- `/app/ci-logs/failed-run.json`: workflow run, suite, test file, test title, status, and retry metadata.
- `/app/ci-logs/job-74291.log`: the failing GitHub Actions job log excerpt.
- `/app/repo/test/checkout/e2e.spec.ts`: the relevant Playwright test file.
- `/app/repo/package.json`: the available scripts for this repository.

Your task:

1. Extract the suite name, test file, exact test title, and CI error from the exported CI logs.
2. Reproduce the failure path with the repository's local scripts. The reproduction must be targeted to the failing suite and exact Playwright test title, and it must compare normal dev behavior with production-bundled behavior before you classify the flake.
3. Use the observed dev/prod reproduction results to classify the flake.
4. Write `/app/triage/flake_report.json`.
5. Write `/app/triage/reproduction_notes.md`.
6. Write `/app/triage/recommended_fix.diff` as a standard unified diff. The diff does not need to be applied, but it must target the real test file and address the observed root cause.

Output format:

`/app/triage/flake_report.json` must be valid JSON with this structure:

```json
{
  "suite": "string",
  "test_file": "string",
  "test_title": "string",
  "ci_error": "string",
  "dev_reproduction": "pass | fail | not_run",
  "prod_reproduction": "pass | fail | not_run",
  "classification": "dev_repro_failure | prod_bundle_regression | unreproduced_ci_only",
  "root_cause": "string",
  "recommended_fix": "string",
  "commands_run": ["string"]
}
```

`/app/triage/reproduction_notes.md` must include:

- Extracted CI details.
- Dev reproduction result.
- Production-bundled reproduction result.
- Final classification.
- Recommended fix summary.

`/app/triage/recommended_fix.diff` must:

- Be a standard unified diff.
- Reference `test/checkout/e2e.spec.ts`.
- Replace the timing-prone assertion with a condition-based Playwright assertion or wait.

Notes:

- Do not modify or delete `/app/ci-logs`.
- Do not replace the mocked test runner or fake the command trace.
- Do not skip the reproduction workflow and infer the answer only from logs.
- Do not run the full test suite when the exact failing test title is available.
- Do not disable the failing test, delete assertions, or change the business flow being tested.
