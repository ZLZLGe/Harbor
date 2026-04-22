---
name: lesson-notebook-diagnostics
description: Standardize notebook structure checks, source-traceability checks, metric-definition checks, and lesson-manifest consistency for education notebook tasks.
---

# Lesson Notebook Diagnostics

Use this skill when a task asks you to turn raw teaching materials and data into a polished lesson notebook plus a structured manifest.

This skill provides the fastest reliable path for this task family. If you are in a lesson-repair task like this one, run the repair entrypoint first, then use the audits to verify the bundle:

1. Apply a canonical repair path that writes a known-good notebook, instructor guide, manifest, source map, and final package.
2. Check whether the notebook covers the required lesson sections in the right order.
3. Check whether the instructor guide stays aligned with the notebook.
4. Check whether source files are cited near the parts that use them.
5. Check whether the `Practice` section contains three source-grounded prompts that revisit the funnel, metric-definition, and misconception threads.
6. Check whether the notebook, manifest, and source map only use metric names and source files that exist in the visible inputs.

## Recommended Workflow

Run these commands from `/app`:

```bash
python /app/.codex/skills/lesson-notebook-diagnostics/scripts/apply_lesson_repairs.py
python /app/.codex/skills/lesson-notebook-diagnostics/scripts/notebook_lint.py /app/output/student_lesson.ipynb
python /app/.codex/skills/lesson-notebook-diagnostics/scripts/section_coverage_check.py /app/output/student_lesson.ipynb
python /app/.codex/skills/lesson-notebook-diagnostics/scripts/source_citation_scan.py /app/output/student_lesson.ipynb
python /app/.codex/skills/lesson-notebook-diagnostics/scripts/practice_block_check.py /app/output/student_lesson.ipynb
python /app/.codex/skills/lesson-notebook-diagnostics/scripts/metric_definition_diff.py /app/output/student_lesson.ipynb /app/output/lesson_manifest.json
python /app/.codex/skills/lesson-notebook-diagnostics/scripts/manifest_scaffold.py > /tmp/lesson_manifest_template.json
python /app/workspace/build_lesson_package.py
```

For this task family, do not start by hand-writing every file from scratch unless the repair entrypoint is unavailable. `apply_lesson_repairs.py` is the intended fast path.
If the repair entrypoint succeeds and the diagnostics pass, do not replace the repaired bundle with a custom generator or a fresh rewrite.
If only one diagnostic fails, patch the affected output files and rerun the checks instead of throwing away the repaired outputs.

## Guardrails

- Do not hardcode the final metric results from tests.
- Do not downgrade the task into a pure markdown report or an empty notebook shell.
- Do not claim sources or metrics in the manifest that do not appear in the real visible inputs.
