#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR=/workspace/reports
REPORT_FILE=$REPORT_DIR/docs-build-investigation.md
REPO_DIR=/workspace/repo

mkdir -p "$REPORT_DIR"

cat <<'EOF' > "$REPORT_FILE"
# PR #218 docs build investigation

## Failed jobs
- docs-build
- docs-preview-smoke

## Failure point
Both jobs fail in the `Install docs dependencies` step defined in `.github/workflows/docs-site.yml`.
The failing command is `npm ci` inside `docs/`.

## Key evidence
- `ci_artifacts/logs/docs-build.log` reports: `npm ci can only install packages when your package.json and package-lock.json are in sync`.
- The same log names the missing entry as `@harbor/theme-utils@file:../packages/theme-utils`.
- `ci_artifacts/logs/docs-preview-smoke.log` fails with the same missing package from the lock file.

## Root cause
`docs/package.json` already depends on `@harbor/theme-utils`, but `docs/package-lock.json` was not regenerated after that dependency was added.
Because the workflow uses `npm ci`, CI refuses to install with the stale lock file and never reaches the docs build step.

## Fix plan
Regenerate `docs/package-lock.json` so it matches `docs/package.json`, then rerun `scripts/run_docs_ci.sh` to confirm the docs build completes.
EOF

cd "$REPO_DIR/docs"
npm install --package-lock-only --ignore-scripts

cd "$REPO_DIR"
bash scripts/run_docs_ci.sh
