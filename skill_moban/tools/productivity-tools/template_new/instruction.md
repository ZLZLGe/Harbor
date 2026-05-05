You are preparing the morning monitoring brief for the Developer Productivity team.

Input data is available in `/app/data`:
- `watchlist.yaml`: monitored sources and source aliases.
- `monitoring_rules.md`: relevance rules, priority rules, and delivery requirements.
- `state/last_scan.json`: the checkpoint from the previous completed run.
- `mirror/site/feeds/`: local copies of RSS and Atom feeds.
- `mirror/site/articles/`: local copies of article pages referenced by those feeds.

Your task:
1. Find every article that appears after the recorded checkpoint.
2. Keep only the new items that satisfy the monitoring rules.
3. Merge repeated references to the same article across sources.
4. Produce a team digest and record each skipped new item with a reason.

Output:
- `/app/output/feed_digest.json`
- `/app/output/feed_digest.md`

`feed_digest.json` must use this structure:

```json
{
  "checkpoint_used": "string",
  "new_relevant_items": [
    {
      "id": "string",
      "title": "string",
      "canonical_url": "string",
      "published_at": "string",
      "sources": ["string"],
      "priority": "high|medium|low",
      "topic": "release|deprecation|security|workflow",
      "summary": "string",
      "why_relevant": "string"
    }
  ],
  "skipped_items": [
    {
      "title": "string",
      "canonical_url": "string",
      "sources": ["string"],
      "skip_reason": "before_checkpoint|out_of_scope|duplicate"
    }
  ]
}
```

`feed_digest.md` must:
- start with `# Developer Productivity Feed Brief`
- include the sections `## High Priority`, `## Medium Priority`, and `## Low Priority`
- list each included item once
- include the title, published date, source aliases, and a one-sentence summary for each listed item

Notes:
- Use only the files under `/app/data/mirror`.
- Treat `state/last_scan.json` as authoritative.
- Do not modify files under `/app/data`.
- Do not access external websites during the task.
