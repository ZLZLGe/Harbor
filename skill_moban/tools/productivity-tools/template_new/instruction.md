You need to complete an engineering release watch workspace for a terminal-based update digest. The workspace already includes a digest shell, a tracked-source registry, mirrored public source pages and feed snapshots, a local watch database with prior tracking state, and a delivery contract. Keep the existing build entrypoint, output paths, watch database path, and repeat-run workflow intact.

Input data is in `/app/release-watch/`:
- `drafts/engineering_release_digest.md`: the current digest shell. It already includes the title, section order, source-coverage shell, and review residue.
- `contracts/digest_contract.json`: the delivery contract. It defines the required sections, output files, watch database path, audit log file, local mirror port, ranking rules, cleanup rules, legacy-blog handling, and repeat-run behavior.
- `data/watch_targets.csv`: the tracked source registry with source ids, labels, priority tiers, public source URLs, local mirror snapshot paths, and optional feed override fields.
- `data/mirror/`: mirrored public HTML pages and RSS/Atom snapshots for this task.
- `seed/initial_watch_state.json`: the seeded watch-state reference used by the local workflow when the watch database needs to be restored.
- `notes/editor_notes.md`: delivery reminders and copy constraints.
- `/app/workspace/build_digest.py`: the formal local build entrypoint for this delivery. Keep it usable so the team can rerun the same workflow from the current inputs.

Your tasks
1. Complete the local watch workflow and generate `/app/output/engineering_release_digest.md`.
2. Use `digest_contract.json`, `watch_targets.csv`, the mirrored sources, and the existing watch database as the source of truth for source onboarding, scan scope, cleanup, prior read history, and repeat-run behavior.
3. Keep the watch database aligned to the tracked-source registry: add missing tracked sources, keep the expected tracked sources, and remove tracked blogs that are no longer present in the registry.
4. Resolve the applicable feed snapshot for each tracked source from the bundled mirrors, scan the tracked sources through the local watch workflow, and preserve the seeded read history that already exists in the watch database.
5. Apply the contract-defined per-source delivery cap to the unread backlog for this run. Deliver only the highest-ranked unread items that fit within that cap for each tracked source.
6. After a successful delivery, mark only the items delivered in this run as read in the same watch database. Leave lower-ranked unread backlog items unread so later reruns over unchanged inputs can continue the backlog until it is exhausted.
7. Generate `/app/output/feed_inventory.json` with the tracked sources, resolved feed references, content format, total article counts, unread article counts before delivery, latest published timestamps, and removed legacy blog names required by the contract.
8. Generate `/app/output/delivery_manifest.json` with the final delivered article URLs, read-marked article URLs, tracked source ids, removed legacy blog names, source-of-truth files used for watch-state restoration and feed resolution, watch database path, and delivery notes required by the contract.
9. Maintain the contract-defined audit log during each build run. Record every local `blogwatcher add`, `remove`, the top-level `scan`, and each per-article `read` command executed for this run as a separate audit event. Use the exact stage value `build`, keep the recorded `args` list aligned to the CLI invocation after `blogwatcher`, and do not use `read-all` while unread backlog remains for later runs.
10. Clean the final deliverables for review. Do not leave placeholder bullets, TODO text, scratch notes, raw XML fragments, or duplicate article entries in the final outputs.
11. Treat bundled mirror files as delivery evidence: when you record a resolved feed reference or a source file from the bundle, use a bundle-relative path that keeps the `data/` prefix.
12. In `## Source Coverage`, if this run removes any legacy blogs while reconciling the watch database, add a short `Removed legacy blogs for this run:` list and include each removed blog name once.

Output
- Update the formal delivery code under `/app/workspace/` and add only a very small helper there if it is strictly necessary for the build entrypoint.
- Create only these files under `/app/output/`:
  - `engineering_release_digest.md`
  - `feed_inventory.json`
  - `delivery_manifest.json`

`engineering_release_digest.md` must:
- include the title `# Engineering Release Watch`
- include the sections `## High Priority` and `## Standard Priority` in that order
- list delivered items as Markdown bullets under the applicable section
- include the source label, article title, published date, and article URL in each delivery bullet
- write `No new items.` under a required section when that section has no delivered items
- keep `## Source Coverage` in the digest and list removed legacy blog names there when any were removed during this run

`feed_inventory.json` must include:

```json
{
  "tracked_sources": [
    {
      "source_id": "string",
      "label": "string",
      "priority_tier": "string",
      "homepage_url": "string",
      "resolved_feed_reference": "bundle-relative data/... path string",
      "content_format": "rss|atom",
      "article_count": 0,
      "unread_count": 0,
      "latest_published_at": "ISO-8601 string"
    }
  ],
  "removed_blog_names": ["string"],
  "notes": ["string"]
}
```

`delivery_manifest.json` must include:

```json
{
  "digest_path": "engineering_release_digest.md",
  "delivered_article_urls": ["string"],
  "read_marked_article_urls": ["string"],
  "tracked_source_ids": ["string"],
  "removed_blog_names": ["string"],
  "source_files": ["bundle-relative source-of-truth path string"],
  "state_db_path": "string",
  "notes": ["string"]
}
```

Notes
- Do not modify the bundled inputs under `/app/release-watch/`.
- Keep repeat-run tracking in the contract-defined watch database file; it is part of the required workflow even though it is not an `/app/output/` deliverable.
- Keep the contract-defined audit log file in the workspace. It is part of the required workflow even though it is not an `/app/output/` deliverable.
- Preserve prior read history that is already present in the watch database. Do not re-deliver items that were already marked read before this run.
- Leave undelivered unread backlog items unread so unchanged reruns can continue them in later batches.
- Do not bulk-mark all unread items as read when the contract still leaves backlog for later reruns.
- Do not change the required output paths or filenames.
- In `delivery_manifest.json`, write the contract-defined watch database file string in `state_db_path`. Do not expand it to an absolute path.
- `resolved_feed_reference` values and bundled mirror entries in `source_files` should stay bundle-relative and keep their `data/` prefix.
- If a source uses its homepage mirror to discover a feed, include both the homepage snapshot path and the resolved feed snapshot path in `source_files`. If a source uses a feed override, include that feed snapshot path.
- Sort `source_files` lexicographically before writing `delivery_manifest.json`.
- `source_files` is an audit list of the source-of-truth files used for watch-state restoration and feed resolution in this run. Do not add presentation-only or reminder-only files there.
- Do not modify the tests, validation logic, pinned dependencies, or environment configuration.
- Do not replace the existing watch database workflow with a one-off parser, a hardcoded final output, or a manual submission that bypasses the formal build entrypoint.
- Do not remove tracked sources from the registry, collapse them into a single source, or narrow the delivery to only one feed format.
- The output directory is a delivery directory. When the task ends, it must contain only the required deliverables.
