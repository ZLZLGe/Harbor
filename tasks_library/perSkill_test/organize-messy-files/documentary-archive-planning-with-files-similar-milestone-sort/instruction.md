You are working in `/root`.

An unsorted documentary archive has been dropped into `/root/documentary_archive/inbox`. The files cover six production milestones, and every file belongs to exactly one of these folders:

1. `01_development`
2. `02_pre_production`
3. `03_production`
4. `04_post_production`
5. `05_festival_delivery`
6. `06_finance_and_admin`

Your job:

1. Read the PDFs, DOCX, PPTX, transcripts, and budget spreadsheets in `/root/documentary_archive/inbox`.
2. Create the six milestone folders directly under `/root/documentary_archive/`.
3. Move every archive file out of `inbox` into the correct milestone folder.
4. Keep every original filename exactly unchanged.
5. Leave no supported archive files behind in `inbox`.
6. Create `/root/reports/archive_manifest.json`.
7. Keep three working notes in `/root` while you work:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`

The manifest must be valid JSON with this shape:

```json
{
  "archive_root": "/root/documentary_archive",
  "inbox_cleared": true,
  "total_files": 24,
  "milestones": [
    {
      "folder": "01_development",
      "scope": "short human-readable description of what belongs in this folder",
      "file_count": 4,
      "files": ["alphabetically sorted filenames"]
    }
  ]
}
```

Requirements for the manifest:

- `milestones` must contain all six folders exactly once.
- Keep the milestone entries sorted by folder name.
- Keep each `files` list alphabetically sorted.
- `file_count` must match the number of files actually placed in that folder.
- `scope` must be a non-empty sentence that describes the folder's coverage.

You may inspect the PDF files with tools such as `pdftotext`, and the office files are ordinary zip-based XML packages that can be inspected with `unzip -p` or Python.
