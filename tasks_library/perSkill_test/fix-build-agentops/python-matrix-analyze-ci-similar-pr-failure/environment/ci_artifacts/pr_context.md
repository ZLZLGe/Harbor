# PR #1421: keep Python matrix labels readable in test reports

- Repository snapshot: `/workspace/repo`
- Workflow under review: `.github/workflows/python-tests.yml`
- Failing jobs:
  - `unit-tests (3.10)`
  - `unit-tests (3.11)`
- Changed files in this PR:
  - `src/prstatus/summary.py`
  - `tests/test_summary.py`
  - `.github/workflows/python-tests.yml`

The author says the change should only affect how matrix job labels appear in generated PR summaries.
Captured job logs from the failed GitHub Actions run are stored in `/workspace/ci_artifacts/logs/`.
