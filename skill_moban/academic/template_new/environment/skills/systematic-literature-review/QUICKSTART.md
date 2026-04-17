# Systematic Review Skill Quickstart

If you want the fastest reliable path in this task, run:

```bash
python /app/apply_review_repairs.py
```

That command rewrites the three official deliverables:

- `/app/workspace/included_studies.csv`
- `/app/workspace/references.bib`
- `/app/workspace/summary.md`

and then runs the official build:

```bash
python /app/workspace/build_submission.py
```

If you need to inspect the reasoning before writing files, use the detailed audits in:

- `/app/.codex/skills/systematic-literature-review/scripts/`
