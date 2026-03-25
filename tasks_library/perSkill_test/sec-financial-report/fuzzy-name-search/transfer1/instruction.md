An analyst left a batch file of misspelled manager references in `/root/data/manager_queries.csv`.

For each row, resolve the best matching filing manager in the specified quarter and write `/root/fund_resolution_table.csv`.

Use this exact CSV schema and preserve the input row order:

```text
row_id,quarter,alias,accession_number,manager_name,manager_city,manager_state
```
