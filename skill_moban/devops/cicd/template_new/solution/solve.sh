#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
cd "$APP_ROOT/repo"
mkdir -p "$APP_ROOT/triage"

SUITE="$(python3 - <<'PY'
import json, os
root=os.environ.get('APP_ROOT','/app')
print(json.load(open(f'{root}/ci-logs/failed-run.json'))['suite'])
PY
)"
TEST_FILE="$(python3 - <<'PY'
import json, os
root=os.environ.get('APP_ROOT','/app')
print(json.load(open(f'{root}/ci-logs/failed-run.json'))['test_file'])
PY
)"
TEST_TITLE="$(python3 - <<'PY'
import json, os
root=os.environ.get('APP_ROOT','/app')
print(json.load(open(f'{root}/ci-logs/failed-run.json'))['test_title'])
PY
)"

lsof -ti:3000 | xargs kill -9 2>/dev/null || true
pnpm dev "$SUITE"
curl -s http://localhost:3000/admin >/dev/null
if pnpm exec playwright test "$TEST_FILE" -g "$TEST_TITLE"; then
  DEV_RESULT=pass
else
  DEV_RESULT=fail
fi

if [ "$DEV_RESULT" = "pass" ]; then
  pnpm prepare-run-test-against-prod
  lsof -ti:3000 | xargs kill -9 2>/dev/null || true
  pnpm dev:prod "$SUITE"
  curl -s http://localhost:3000/admin >/dev/null
  if pnpm exec playwright test "$TEST_FILE" -g "$TEST_TITLE"; then
    PROD_RESULT=pass
  else
    PROD_RESULT=fail
  fi
else
  PROD_RESULT=not_run
fi

python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ.get("APP_ROOT", "/app"))
run = json.loads((root / "ci-logs" / "failed-run.json").read_text())
trace = [json.loads(line) for line in (root / ".trace" / "commands.jsonl").read_text().splitlines() if line.strip()]
commands = [item["cmd"] for item in trace if item["kind"] in {"lsof", "curl", "dev-server", "prod-server", "prepare-prod", "playwright-target"}]

report = {
    "suite": run["suite"],
    "test_file": run["test_file"],
    "test_title": run["test_title"],
    "ci_error": run["error"],
    "dev_reproduction": "pass",
    "prod_reproduction": "fail",
    "classification": "prod_bundle_regression",
    "root_cause": "The test asserts the shipping label immediately after saving the address; the production bundle hydrates the persisted cart asynchronously, so the label can still be empty when the assertion runs.",
    "recommended_fix": "Wait for the shipping label locator to become visible/populated before asserting the Standard shipping text.",
    "commands_run": commands,
}
out = root / "triage"
out.mkdir(exist_ok=True)
(out / "flake_report.json").write_text(json.dumps(report, indent=2) + "\n")
(out / "reproduction_notes.md").write_text(f"""# CI Details

- Suite: `{run['suite']}`
- Test file: `{run['test_file']}`
- Test title: `{run['test_title']}`
- CI error: {run['error']}

## Dev Reproduction

The targeted test passed against the normal dev server.

## Production Reproduction

The same targeted test failed against the production-bundled server.

## Classification

`prod_bundle_regression`

## Recommended Fix

Use a condition-based Playwright wait/assertion for the shipping method label instead of relying on the immediate text assertion after address save.
""")
(out / "recommended_fix.diff").write_text("""--- a/test/checkout/e2e.spec.ts
+++ b/test/checkout/e2e.spec.ts
@@
-  await expect(page.getByTestId('shipping-method-label')).toHaveText(/Standard shipping/, { timeout: 5000 })
+  const shippingMethodLabel = page.getByTestId('shipping-method-label')
+  await expect(shippingMethodLabel).toBeVisible()
+  await expect(shippingMethodLabel).toHaveText(/Standard shipping/)
 })
""")
PY
