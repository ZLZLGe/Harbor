#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR=/workspace/reports
REPORT_FILE=$REPORT_DIR/pr-triage.md
REPO_DIR=/workspace/repo

mkdir -p "$REPORT_DIR"

cat <<'EOF' > "$REPORT_FILE"
# PR #1421 triage

## Failing jobs
- unit-tests (3.10)
- unit-tests (3.11)

## Key evidence
- Both logs fail in `tests.test_summary.TestJobSummary.test_format_python_job_preserves_dot`.
- The 3.11 log also shows `tests.test_summary.TestJobSummary.test_build_report_title_uses_matrix_label` failing because the generated label is `python-311` instead of `python-3.11`.
- The failures point to `src/prstatus/summary.py`, specifically `format_python_job`.

## Root cause
`format_python_job` removes the dot from the Python version string by returning `python-{major}{minor}`.
That breaks the matrix label format for every tested Python version.

## Fix plan
Preserve the dot between major and minor versions in `format_python_job`, then rerun `scripts/run_pr_matrix.sh`.
EOF

python - <<'PY'
from pathlib import Path

path = Path("/workspace/repo/src/prstatus/summary.py")
text = path.read_text()
old = '    return f"python-{major}{minor}"\n'
new = '    return f"python-{major}.{minor}"\n'
if old not in text:
    raise SystemExit("expected buggy line not found")
path.write_text(text.replace(old, new))
PY

cd "$REPO_DIR"
bash scripts/run_pr_matrix.sh
