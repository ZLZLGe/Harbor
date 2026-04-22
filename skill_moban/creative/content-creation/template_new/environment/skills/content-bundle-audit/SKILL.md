---
name: content-bundle-audit
description: Audit a multi-channel launch content pack against frozen source materials, focusing on confirmed facts, forbidden claims, channel-specific constraints, and final bundle packaging.
metadata:
  short-description: Audit launch content bundles
---

# content-bundle-audit

Use this skill when the task is to produce a multi-channel content pack from frozen source materials such as a launch brief, fact sheet, voice guide, and keyword plan.

This skill does not give you the final copy. Its value is to make the workflow repeatable:

1. Extract the confirmed facts and forbidden claims.
2. Separate confirmed launch facts from roadmap or internal-only notes.
3. Check the hard constraints for each channel.
4. Audit whether the outputs are too similar to each other.
5. Run the final bundle packaging script.

## Workflow

### 1. Extract the fact matrix

Run:

```bash
python /app/.codex/skills/content-bundle-audit/scripts/fact_matrix.py
```

This prints confirmed facts, forbidden claims, roadmap notes, and the keyword plan in one place before you start writing.

### 2. Check channel stats

Run:

```bash
python /app/.codex/skills/content-bundle-audit/scripts/channel_stats.py
```

This prints word counts, subject length, preview length, hashtag count, and CTA values for the current outputs.

### 3. Audit the current bundle

Run:

```bash
python /app/.codex/skills/content-bundle-audit/scripts/audit_bundle.py
```

This gives you a channel-by-channel checklist for fact coverage, forbidden claims, and cross-channel duplication.

Do not stop after the first draft. If `audit_bundle.py` reports any issue, revise the outputs and run it again until the checklist is clean.

### 4. Package the final bundle

Run:

```bash
python /root/build_bundle.py
```

The final task output is not complete until `/root/publish_bundle.json` is generated successfully.

## Mandatory final checks

Before you stop, verify these exact task-level contracts:

- Blog:
  - H1 includes `content repurposing workflow`
  - The first 120 words mention `SignalLeaf Studio 2.0`, the audience, and the workflow framing
  - The body includes at least two secondary keywords from the keyword plan
- LinkedIn:
  - First non-empty line should stay roughly under 110 characters
  - Must include `April 28, 2026`
  - Must include `Growth` and `Scale`
  - Must include `English only`
  - Must include the official waitlist URL
- Newsletter:
  - `subject` length must stay between 38 and 60 characters
  - `preview_text` length must stay between 60 and 95 characters
  - Body must include the exact date string `April 28, 2026`
  - Body must include `Growth` and `Scale`
  - Body must include `English only`
  - Body must include either `approval queue` or `42%`
- SEO metadata:
  - `primary_keyword` must exactly match the keyword plan
  - `slug` must exactly match the keyword plan
  - `title` length must stay between 50 and 65 characters
  - `description` length must stay between 145 and 165 characters
  - `description` must mention `approval queue`, and should mention either launch availability (`Growth` and `Scale`), the `42%` beta result, or `role-based comments`

Recommended final sequence:

1. Run `fact_matrix.py` before writing.
2. Draft all four deliverables.
3. Run `channel_stats.py` and fix every out-of-range length or count.
4. Run `audit_bundle.py` and fix every remaining issue.
5. Run `python /root/build_bundle.py`.
6. Re-run `channel_stats.py` one last time to confirm the final files still meet the numeric bounds.

## What to watch for

- Facts that are present in one channel but contradicted in another.
- Unsupported claims that sneak in because the language sounds more polished.
- Roadmap items that get promoted into launch messaging.
- LinkedIn hooks that are too long and read like blog sentences instead of feed-native openers.
- LinkedIn or newsletter copy that is too close to the blog post.
- SEO metadata that no longer matches the actual blog content.
