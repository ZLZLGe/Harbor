# Quickstart

1. Read `/app/workspace/lesson_brief.md`.
2. Open `/app/workspace/draft_notebook.ipynb` to see what is already there.
3. Start with `python /app/.codex/skills/lesson-notebook-diagnostics/scripts/apply_lesson_repairs.py`.
4. Run all diagnostic scripts, including `practice_block_check.py`, before you decide anything is done.
5. If the repair path plus diagnostics already pass, keep those repaired outputs; do not replace them with a custom generator.
6. Only fall back to manual rebuilding if the repair entrypoint is unavailable or a specific diagnostic still fails after targeted fixes.
7. Run `python /app/workspace/build_lesson_package.py` before the final verifier pass.
