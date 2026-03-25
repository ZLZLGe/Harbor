The shortlist in `/root/data/q3_accessions.txt` contains q3 accession numbers for several managers.

Write `/root/q3_manager_league.tsv` as a tab-separated file with this exact header:

```text
accession	manager_name	total_aum	stock_holdings
```

Rules:

1. Use the q3 snapshot only.
2. Sort rows by `total_aum` descending.
3. If two rows ever tie on `total_aum`, sort those tied rows by accession number ascending.
