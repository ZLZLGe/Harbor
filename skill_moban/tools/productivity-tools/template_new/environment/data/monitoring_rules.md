# Developer Productivity Monitoring Rules

Scope:
- Track developer tooling releases, deprecations, workflow changes, and security updates.
- Use the mirrored article page as the authority for canonical URL, publication time, and summary context.
- Keep only items published after the checkpoint in `state/last_scan.json`.

Topic classification:
- `release`: runtime, CLI, SDK, or platform release announcements, including release candidates and LTS updates.
- `deprecation`: model, feature, or access removals; date-bound shutdowns; contract or availability reductions.
- `security`: vulnerability response, supply-chain compromise analysis, or security program changes with operational impact.
- `workflow`: changes that alter day-to-day developer execution paths, automation behavior, or cost paths.

Out-of-scope items:
- event invitations or event trip reports
- beginner tutorials, explainers, or getting-started guides
- company status updates and retrospectives
- partner marketing pieces and feature spotlights without a required action, deadline, or contract change
- project progress notes that are neither releases nor operational changes

Priority rules:
- `high`: immediate security relevance, a date-bound deprecation, or a cost/billing change with a published effective date.
- `medium`: actionable release or security governance change without an immediate deadline.
- `low`: informative prerelease or minor workflow note that is still in scope.

Delivery rules:
- Merge repeated references to the same article across sources by canonical article URL.
- For merged relevant items, keep all matching source aliases in `sources`.
- Record every skipped new item with one reason from `before_checkpoint`, `out_of_scope`, or `duplicate`.
- Use the article page `description` meta tag or the first meaningful paragraph to build a one-sentence summary.
- Use ISO 8601 UTC timestamps in the output JSON.
