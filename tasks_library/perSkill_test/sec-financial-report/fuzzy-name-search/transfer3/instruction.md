The file `/root/data/mixed_queries.md` contains a mixed watchlist of managers and issuers written with approximate names.

Resolve every entry and write `/root/watchlist_resolution.tsv` with this exact tab-separated header:

```text
kind	query	quarter	resolved_id	resolved_name
```

Rules:

1. Preserve the item order from the markdown file.
2. Use `fund` or `stock` in the `kind` column.
3. Keep the provided quarter for fund rows.
4. Use `-` as the quarter value for stock rows.
