You are preparing a multi-platform content bundle around the AI agent theme for a content team targeting engineers. The team has organized the anchor article, supporting materials, brand/author samples, and publishing constraints in the workspace. They require that all drafts be produced strictly from the provided materials and be suitable for publishing in their respective channels.

Input data is under `/root/workspace/source_bundle/`:

- `source_index.json`: an index of input files, source IDs, asset types, and recommended usage.
- `anchor_article.md`: the anchor article for this content bundle.
- `supporting_context/`: product overview, supporting articles, terminology notes, and allowable background material to cite.
- `voice_samples/`: existing brand/author sample writing.
- `campaign_constraints.json`: audience, channel goals, word-count ranges, CTA constraints, and prohibited content.
- `style_red_flags.txt`: phrasing styles that the content owner explicitly rejects.

The container also provides a local review service for cross-checking the material inventory, line-number citations, and publishing constraints.

Your tasks

1. Read all input materials, determine a unified direction for this release, and produce 3 external deliverables.
2. Based on the provided materials, write an X thread, a LinkedIn post, and a newsletter draft that are suitable for their respective channels.
3. For each deliverable, complete source registration by indicating which input materials support key statements.
4. List items that still require confirmation, additional input, or approval from the content team before publishing.

Output

If `/root/output/` does not exist, create it first. Write all deliverables into `/root/output/`, and create only the following files:

- `campaign_summary.md`
- `x_thread.md`
- `linkedin_post.md`
- `newsletter_draft.md`
- `source_map.json`
- `publish_gaps.json`

Requirements for `campaign_summary.md`:

- The first line must be a single-sentence campaign summary for this release.
- Then write 3 channel lines corresponding to X, LinkedIn, and newsletter.
- Each line must start with `- ` and include the channel name and that channel's content focus.

Requirements for `x_thread.md`:

- Write in English.
- 5 to 7 posts, numbered incrementally as `1/`, `2/`, ...
- The first post must jump straight into the thesis, evidence, or tension.

Requirements for `linkedin_post.md`:

- Write in English.
- 180 to 320 words.
- At most 6 natural paragraphs.
- You may include 1 short list, with no more than 3 list items.

Requirements for `newsletter_draft.md`:

- Write in English.
- The first two lines of the file must start with `Subject:` and `Preview:` respectively.
- Body: 350 to 550 words.
- The body must contain at least 3 `##` level-2 headings.
- The first paragraph must go straight into the topic.

`source_map.json` must match the following structure:

```json
{
  "anchor_asset": "anchor_article.md",
  "deliverables": [
    {
      "file": "x_thread.md",
      "audience": "string",
      "content_focus": "string",
      "source_refs": ["relative/path.md#L10-L20"]
    }
  ],
  "shared_limits": ["string"]
}
```

Requirements:

- `deliverables` must cover `x_thread.md`, `linkedin_post.md`, and `newsletter_draft.md`.
- Each deliverable must include at least 2 `source_refs`.
- `source_refs` may only reference files under `/root/workspace/source_bundle/`.

`publish_gaps.json` must match the following structure:

```json
{
  "gaps": [
    {
      "topic": "string",
      "why_it_matters": "string",
      "needed_from_team": "string"
    }
  ]
}
```

Notes

- You may only use materials under `/root/workspace/source_bundle/` for writing and evidence.
- Do not add customer names, numbers, release dates, feature capabilities, case studies, or quotes that do not appear in the input.
- Do not copy the same text passage directly into multiple channel files.
- Do not modify the input directory, tests, environment files, or any `skills` directory content.
- You may write helper scripts; in the end, submit only the required files under `/root/output/`.
