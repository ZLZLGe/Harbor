You are given two offline HTML snapshots in `/root/archive_snapshots/`. Each page contains one long essay mixed with navigation, archive chrome, recommendation blocks, subscription prompts, and footer noise.

Produce a single spoken anthology from those snapshots.

Requirements:

1. Read `/root/archive_snapshots/reading_order.txt` and keep that chapter order.
2. For each HTML snapshot, extract only the essay body text.
3. Remove page chrome such as menus, newsletter prompts, related links, footer text, comment prompts, and similar noise.
4. Preserve the original body wording and paragraph order. Do not summarize or rewrite the essays.
5. Create `/root/founder-anthology-script.txt` with exactly two chapters. Each chapter must use this structure:

```text
Chapter 1: <title>
Opening: <one sentence introducing the chapter title>

<body paragraphs in original order>
```

6. Generate the final MP3 at the primary output path declared in `task.toml`. The audio should read both chapters in order and include the opening sentence for each chapter.

Notes:

- You may use local or remote speech synthesis, but the task must finish inside the container.
- The verifier will check the script for body coverage and chapter order, and will also check that the MP3 is a decodable audio file.
