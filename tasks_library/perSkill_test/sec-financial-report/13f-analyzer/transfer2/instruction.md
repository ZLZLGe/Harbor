The q3 crowding watchlist in `/root/data/q3_watchlist.csv` lists a few issuer CUSIPs.

For each CUSIP, identify the top q3 holder and write `/root/q3_crowding_watchlist.csv` with this exact CSV schema:

```text
cusip,top_accession,top_manager_name,total_value
```

Keep the same row order as the input file.
