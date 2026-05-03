---
name: content-engine
description: Turn one bundled source packet into channel-specific content assets with grounded source references, a consistent operator voice, and a final self-check pass.
---

# Content Engine

Use this skill when a task asks for a campaign pack, social thread, newsletter draft, content repurposing, or source-grounded multi-channel writing from one bundled source set.

## What This Skill Is Good For

- Converting one anchor asset plus supporting context into multiple outward-facing drafts.
- Building a line-aware source registry before writing so references stay valid.
- Deriving a reusable operator-style voice from sample texts without copying sentences.
- Splitting channels by emphasis so every asset earns its slot.
- Running a final lint pass for source coverage, red-flag phrasing, and cross-channel duplication.

## Recommended Workflow

1. Read `/root/workspace/source_bundle/source_index.json` and `/root/workspace/source_bundle/campaign_constraints.json`.
2. Query the local review service for `/api/index`, `/api/constraints`, and every `/api/document/<doc_id>` entry before drafting.
3. Build a local registry of line-addressable notes so you can cite files and line ranges accurately.
4. Review the `voice_samples/` material and write short scratch notes about rhythm, confidence level, tradeoff language, and repeated proof habits.
5. Assign one clear emphasis to each deliverable before drafting; keep overlap low across channels.
6. Draft the outward-facing assets, then fill in `source_map.json` and `publish_gaps.json` from the same grounded reading.
7. Mirror `required_shared_limits` from `campaign_constraints.json` into `source_map.json` exactly, with the same wording and order.
8. Run the bundle lint script before finalizing, and keep editing until it returns `{"ok": true, "issues": []}`.

## Helper Scripts

- `python3 /root/.codex/skills/content-engine/scripts/build_source_registry.py`
  - Pulls the review-service index, constraints, and every document into one local JSON registry with line-addressable content.
- `python3 /root/.codex/skills/content-engine/scripts/summarize_voice_samples.py`
  - Reads the built registry and prints concise voice cues from the bundled voice samples.
- `python3 /root/.codex/skills/content-engine/scripts/lint_campaign_bundle.py /root/output`
  - Checks output presence, source refs, exact shared limits, red-flag phrasing, channel duplication, and the main per-channel structural constraints.

## Notes

- The task is grounded in the bundled source packet; do not add outside claims.
- The local review service exists to make source coverage and line refs cheaper to validate.
- A good bundle reuses source material, not paragraphs.
