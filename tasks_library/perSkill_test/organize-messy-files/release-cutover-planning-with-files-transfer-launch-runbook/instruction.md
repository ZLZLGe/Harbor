You are working in `/root`.

A release preparation workspace is available at `/root/release_workspace`. It includes product scope notes, a migration plan, a defect register, rollback snippets, validation material, monitoring thresholds, and go/no-go meeting notes for an upcoming production cutover.

Your job:

1. Review the evidence in `/root/release_workspace`.
2. Write `/root/plans/cutover_runbook.md`.
3. Keep three working notes in `/root` while you work:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`

Working note expectations:

- `task_plan.md` should keep a short phase-by-phase plan or checklist for assembling the runbook.
- `findings.md` should capture concrete release facts, thresholds, and risks pulled from the evidence.
- `progress.md` should log completed work and note when `plans/cutover_runbook.md` has been written.

Requirements for `/root/plans/cutover_runbook.md`:

- Use these exact section headings:
  - `# Release Cutover Runbook`
  - `## Release Summary`
  - `## Owner Map`
  - `## Execution Sequence`
  - `## Validation Gates`
  - `## Rollback Triggers`
- In `## Release Summary`, state the release identifier, the maintenance window, the in-scope services, and the feature flags being activated.
- In `## Owner Map`, include all named owners with their release responsibilities.
- In `## Owner Map`, list each named owner separately and describe that person's responsibilities in your own words.
- In `## Execution Sequence`, include one Markdown table with exactly these columns in this exact order:
  - `Step`
  - `Window`
  - `Owner`
  - `Dependencies`
  - `Action`
  - `Verification`
  - `Rollback Trigger`
  - `Evidence`
- The execution table must contain exactly 8 data rows ordered from step 1 through step 8.
- Follow the approved eight-step bridge sequence from the meeting notes so the rows cover the cutover phases in order.
- The `Window` column may use any clear timing notation, but every row must include one.
- Each execution row must make the owner, dependency, verification check, and rollback trigger explicit.
- Each execution row should use concrete evidence, thresholds, checks, or file references from `/root/release_workspace`, not generic placeholders.
- The `Evidence` column must cite specific files from `/root/release_workspace`.
- In `## Validation Gates`, include at least 4 bullet points covering the release-critical checks that must pass after deployment.
- In `## Rollback Triggers`, include at least 4 bullet points that clearly state when to stop or reverse the cutover.

Do not modify the evidence files. The goal is to synthesize them into a launch-day runbook and keep the three working notes as you go.
