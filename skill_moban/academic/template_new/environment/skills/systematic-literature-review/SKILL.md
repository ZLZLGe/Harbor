---
name: systematic-literature-review
description: Structured workflow for repairing a bounded systematic-review evidence package. Use this skill when a task involves screening candidate studies against a protocol, validating bibliography metadata, or checking whether a narrative summary is supported by the currently included evidence.
allowed-tools: Read Write Edit Bash
license: MIT
---

# Systematic Literature Review

## Overview

This skill standardizes three review-ops steps that are easy to miss when working from a sparse candidate export alone:

1. Screen the included study table against the protocol and candidate export.
2. Validate BibTeX entries against canonical metadata for the included studies.
3. Check whether the narrative summary matches the in-scope evidence without overclaiming.

In this environment the public candidate CSV is only a seed list with internal study IDs. The workspace also includes a raw local publication cache, but that cache does not expose the internal `study_id` mapping or canonical extraction labels directly. The helper scripts use the bundled review catalog shipped with this skill to resolve the mapping, derive canonical extraction labels, and then use the local review QA service only for the final black-box validation checks.
If the local validation service is not already running, the summary audit and submission build step will bootstrap it before validating the workspace.

## Recommended Workflow

Run these commands from `/app`:

```bash
python /app/.codex/skills/systematic-literature-review/scripts/apply_repairs.py
python /app/.codex/skills/systematic-literature-review/scripts/audit_all.py
python /app/.codex/skills/systematic-literature-review/scripts/audit_screening.py
python /app/.codex/skills/systematic-literature-review/scripts/audit_bibliography.py
python /app/.codex/skills/systematic-literature-review/scripts/audit_summary.py
python /app/workspace/build_submission.py
```

For the fastest reliable path in this task family, run `apply_repairs.py` first. It reconstructs the canonical included-study table, writes normalized BibTeX entries for the in-scope trials, and rewrites the bounded narrative summary before invoking the official submission build.

## What Good Output Looks Like

- `included_studies.csv` contains only adult type 2 diabetes randomized trials that meet the protocol.
- `references.bib` contains one canonical entry per included study and no out-of-scope leftovers.
- `summary.md` states adult-T2D-only scope, mentions four randomized trials, acknowledges benefit relative to passive controls, and avoids claiming consistent superiority over active diet comparators.

## Helper Scripts

- `apply_repairs.py`: writes the canonical review package back to the official workspace files and then runs the official submission build for verification.
- `audit_all.py`: runs the three audits in sequence so you can see the full repair plan first.
- `audit_screening.py`: derives the canonical study rows from the bundled review catalog and reports missing studies, removals, and field-level repairs.
- `audit_bibliography.py`: reports missing bibliography entries, extra citations, and the exact metadata fields that still need repair.
- `audit_summary.py`: reports missing or forbidden summary claim categories and groups the supporting evidence into passive-control benefit versus active-comparator limitation buckets.
