---
name: launch-deck-diagnostics
description: Use when the task mentions browser-native HTML deck delivery, `/app/output/deck/index.html`, `weekly_kpis.csv`, `feature_matrix.csv`, `customer_quotes.json`, `user_journey.json`, or a localhost `manifest -> validate` QA chain. Standardize rapid contract diagnosis, source-trace packaging, and real QA submission for Harbor design deck tasks.
---

# launch-deck-diagnostics

Use this skill when the task is to deliver a browser-native HTML deck from frozen brand, KPI, comparison, quote, and journey inputs, especially when success also requires:

- `/app/workspace/drafts/internal_review_draft.html`
- `/app/output/deck/index.html`
- `/app/output/deck_submission.json`
- `/app/output/deck_receipt.json`
- a live localhost `manifest -> validate` chain

This skill is meant to fire on exactly the kind of task that references `weekly_kpis.csv`, `feature_matrix.csv`, `customer_quotes.json`, `user_journey.json`, slide roles, and browser viewport constraints.

This skill does not design the deck for you. Its value is to make the highest-risk parts of the workflow repeatable:

1. Probe the live manifest and view the contract before editing the deck.
2. Check whether the current HTML violates the slide, navigation, overflow, and browser-layout contract.
3. Confirm that source trace, KPI fidelity, comparison fidelity, quote usage, and journey-diagram coverage are real.
4. Package the final submission from the current HTML.
5. Submit the final payload to the localhost QA service and verify the returned receipt.

## Fast Start

Do this early, before spending long on speculative design tweaks:

1. Read:
   - `/app/workspace/brief/creative_brief.md`
   - `/app/workspace/specs/deck_contract.md`
2. Probe the live contract first:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/probe_manifest.py`
3. If `/app/output/deck/index.html` does not exist but `/app/workspace/drafts/internal_review_draft.html` does, stage that internal-review draft into the formal output path first:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/stage_internal_review_draft.py`
4. If `/app/output/deck/index.html` already exists, treat it as the current draft and run lightweight triage before making broad design changes:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/run_full_diagnostics.py`
5. If the current draft already passes structure checks but still needs fidelity cleanup, repair the seeded fidelity markers before attempting final submit:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/repair_story_fidelity_seed.py`
6. Only if the draft is missing, corrupted, or structurally unusable, create a compliant starter deck first:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/bootstrap_deck.py`
7. Use that triage output to decide whether you are blocked on:
   - missing slide structure
   - missing source traces
   - missing KPI or journey coverage
   - obvious overflow or navigation failures

If the draft already covers the six slides and source hooks, avoid rewriting it from scratch before you know which contract or fidelity checks are failing.
If the deck does not exist yet, do not hand-build the whole structure from scratch unless you need a custom direction. Start from the bootstrap output, then refine.
Only run the final validation chain after the content and structure are already close:

- `python /app/.codex/skills/launch-deck-diagnostics/scripts/run_full_diagnostics.py --final`

## Recommended workflow

1. Read:
   - `/app/workspace/brief/creative_brief.md`
   - `/app/workspace/specs/deck_contract.md`
2. Probe the live contract:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/probe_manifest.py`
3. If the formal output deck does not exist but the internal-review draft exists, stage it first:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/stage_internal_review_draft.py`
4. If the draft exists, run lightweight triage before editing:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/run_full_diagnostics.py`
5. If the draft already looks structurally complete, repair the seeded fidelity markers before broad redesign:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/repair_story_fidelity_seed.py`
6. If the draft is missing or unusable, generate a compliant starter deck:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/bootstrap_deck.py`
7. While shaping the deck, use targeted checks instead of jumping straight to final submit:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/check_overflow.py`
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/check_navigation.py`
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/check_source_trace.py`
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/check_chart_and_diagram_coverage.py`
8. Once layout and content are stable, run the heavier checks:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/check_browser_contract.py`
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/check_story_fidelity.py`
9. After the deck HTML is ready, package and submit only once you are close to done:
   - `python /app/.codex/skills/launch-deck-diagnostics/scripts/run_full_diagnostics.py --final`

## Guardrails

- Do not hardcode KPI values, slide titles, source refs, node counts, or receipt fields from the tests.
- Do not skip the live `POST /validate` chain.
- Do not replace structured chart or journey output with screenshots.
- Do not remove slide roles, navigation, or source labels to make diagnostics quieter.
- Probe scripts are for diagnosis and packaging only. The final task output is still the real deck and the real receipt.
