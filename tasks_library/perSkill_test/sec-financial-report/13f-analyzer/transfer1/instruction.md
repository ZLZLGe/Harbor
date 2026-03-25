The file `/root/data/fund_pairs.csv` lists q3 and q2 accession-number pairs for two managers.

For each row, compare the q3 filing against the q2 baseline and write `/root/rotation_digest.csv` with this exact CSV schema:

```text
fund_label,q3_accession,q3_total_aum,largest_buy_cusip,largest_sell_cusip
```

Use the same row order as the input file.
