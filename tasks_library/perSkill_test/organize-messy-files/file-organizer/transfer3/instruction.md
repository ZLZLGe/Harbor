Documents in `/root/desk` need to be filed into a finance archive.

Use `/root/data/finance_manifest.json` as the source of truth for each file's `year` and `category`.

Required structure:
- `/root/finance/<year>/<category>/<filename>`

Rules:
- move every listed file into its exact target folder
- do not rename files
- after processing, `/root/desk` must not contain any listed file

Create `/root/transfer3_finance_index.csv` with columns:
- `year`
- `category`
- `file`
- `target`
- `size_bytes`

Sort rows by `year`, then `category`, then `file`.
