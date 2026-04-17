# Template New Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify the single-container `template_new` task passes `harbor run oracle` in daytona cloud containers and produces a real `without_skill` Harbor result that does not fully pass, while preserving README quality, realism, and verifier reliability.

**Architecture:** Treat this as a validation-first debugging loop. First confirm the task definition, environment shape, and existing runtime artifacts; then run the authoritative Harbor entrypoints (`oracle`, `without_skill`, `with_skill`) under the required environment settings; only if those runs expose a real task defect, patch the minimal source files in `template_new` and re-run the exact failing command.

**Tech Stack:** Harbor task runner, daytona remote environments, Docker single-container task image, pytest verifier, Playwright-based browser checks, shell automation.

---

### Task 1: Confirm single-container task shape and runtime entrypoints

**Files:**
- Modify: `docs/superpowers/plans/2026-04-10-template-new-validation.md`
- Verify: `task.toml`
- Verify: `README.md`
- Verify: `instruction.md`
- Verify: `environment/Dockerfile`

- [ ] **Step 1: Inspect the task definition and layout**

Run: `cd /home/lenovo/skill/Harbor/skill_moban/debugging/template_new && test ! -f environment/docker-compose.yml && sed -n '1,220p' task.toml && find . -maxdepth 2 -type f | sort`

Expected: no `environment/docker-compose.yml`, task metadata loads, and only Dockerfile-based environment files remain.

- [ ] **Step 2: Inspect README and instruction text for the current behavioral contract**

Run: `cd /home/lenovo/skill/Harbor/skill_moban/debugging/template_new && rg -n "single|linked alert|drawer|oracle|without_skill|with_skill|daytona" README.md instruction.md tests -S`

Expected: documentation and verifier wording match the linked-alert drawer-scoping requirement and single-container positioning.

### Task 2: Run daytona oracle and capture authoritative pass evidence

**Files:**
- Verify: `task.toml`
- Verify: `tests/test.sh`
- Output: `/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/*`

- [ ] **Step 1: Export the required cloud-run environment variables**

Run:

```bash
export DAYTONA_API_KEY='dtn_bc05d2fa2efe1df2d2f1fb8d589d1ffd9d85cf33c1f53153efe48c4f05449c88'
export HARBOR_ENV_TYPE='daytona'
export HARBOR_CONCURRENCY='2'
export PER_SKILL_PREFIX_RANGE='[q-r]'
source /mnt/e/tools/harbor-env.sh
```

Expected: `harbor` resolves in shell and the environment is ready for remote execution.

- [ ] **Step 2: Run the exact oracle command against source `template_new`**

Run:

```bash
harbor run -p /home/lenovo/skill/Harbor/skill_moban/debugging/template_new -a oracle --force-build --job-name template-new-oracle-daytona-20260410 -o /home/lenovo/.tmp_debugging_validation/runtime/codex_runs
```

Expected: Harbor completes successfully, verifier passes, and reward is `1`.

- [ ] **Step 3: Inspect oracle outputs instead of trusting the CLI summary**

Run: `find /home/lenovo/.tmp_debugging_validation/runtime/codex_runs/template-new-oracle-daytona-20260410 -maxdepth 3 -type f | sort`

Expected: result files, verifier logs, and reward files exist for the completed job.

### Task 3: Produce a real `without_skill` non-full-pass result

**Files:**
- Verify: `tests/verify_dashboard.py`
- Verify: `tests/test_performance.py`
- Output: `/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/*`

- [ ] **Step 1: Reuse the same cloud environment exports**

Run:

```bash
export DAYTONA_API_KEY='dtn_bc05d2fa2efe1df2d2f1fb8d589d1ffd9d85cf33c1f53153efe48c4f05449c88'
export HARBOR_ENV_TYPE='daytona'
export HARBOR_CONCURRENCY='2'
export PER_SKILL_PREFIX_RANGE='[q-r]'
source /mnt/e/tools/harbor-env.sh
```

Expected: the shell remains configured for Harbor daytona runs.

- [ ] **Step 2: Run the exact `without_skill` task until a completed verifier result is produced**

Run:

```bash
harbor run -p /home/lenovo/skill/Harbor/skill_moban/debugging/template_new -a without_skill --model openai/codex-gpt-5.4 --force-build --job-name template-new-without-skill-daytona-20260410 -o /home/lenovo/.tmp_debugging_validation/runtime/codex_runs
```

Expected: Harbor completes with a finished verifier result and total reward less than perfect.

- [ ] **Step 3: Inspect the verifier output and count real passes/failures**

Run:

```bash
find /home/lenovo/.tmp_debugging_validation/runtime/codex_runs/template-new-without-skill-daytona-20260410 -maxdepth 3 -type f | sort
```

Expected: logs show a real test result, not an infrastructure failure, and the score is below full pass.

### Task 4: Capture a fresh `with_skill` comparison run

**Files:**
- Output: `/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/*`

- [ ] **Step 1: Run a fresh `with_skill` Harbor job**

Run:

```bash
export DAYTONA_API_KEY='dtn_bc05d2fa2efe1df2d2f1fb8d589d1ffd9d85cf33c1f53153efe48c4f05449c88'
export HARBOR_ENV_TYPE='daytona'
export HARBOR_CONCURRENCY='2'
export PER_SKILL_PREFIX_RANGE='[q-r]'
source /mnt/e/tools/harbor-env.sh
harbor run -p /home/lenovo/skill/Harbor/skill_moban/debugging/template_new -a with_skill --model openai/codex-gpt-5.4 --force-build --job-name template-new-with-skill-daytona-20260410 -o /home/lenovo/.tmp_debugging_validation/runtime/codex_runs
```

Expected: job finishes and exposes the same timing/token metadata paths as the `without_skill` run.

- [ ] **Step 2: Extract timing and token usage from both jobs**

Run:

```bash
for job in \
  /home/lenovo/.tmp_debugging_validation/runtime/codex_runs/template-new-without-skill-daytona-20260410 \
  /home/lenovo/.tmp_debugging_validation/runtime/codex_runs/template-new-with-skill-daytona-20260410
do
  echo "=== $job ==="
  find "$job" -maxdepth 3 -type f | sort
done
```

Expected: enough metadata exists to compare wall-clock duration and token consumption between the two runs.

### Task 5: If verification fails for task reasons, patch minimally and re-run the exact failing command

**Files:**
- Modify: `README.md`
- Modify: `instruction.md`
- Modify: `tests/verify_dashboard.py`
- Modify: `tests/test_performance.py`
- Modify: `environment/website/src/components/DashboardShell.tsx`
- Modify: `environment/website/src/components/AlertDrawer.tsx`
- Modify: `solution/fixed/src/components/DashboardShell.tsx`
- Modify: `solution/fixed/src/components/AlertDrawer.tsx`
- Modify: `solution/solve.sh`

- [ ] **Step 1: Read the exact failure logs and identify one root cause**

Run: `sed -n '1,240p' <failing-job-log-or-pytest-output>`

Expected: a concrete failure mode is identified before any edit is attempted.

- [ ] **Step 2: Apply one minimal source fix that addresses that root cause**

Run: `git diff -- /home/lenovo/skill/Harbor/skill_moban/debugging/template_new`

Expected: only task-relevant files change, with no unrelated churn.

- [ ] **Step 3: Re-run the exact previously failing Harbor command**

Run: `<same failing harbor run command>`

Expected: the prior failure is resolved or a new root cause becomes visible for the next loop.
