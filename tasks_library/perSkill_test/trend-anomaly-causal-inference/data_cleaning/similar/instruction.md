Clean the supplied shopper order ledger so it can be used in downstream reporting.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/similar_shopper_orders_cleaned.csv`
- `/root/similar_shopper_orders_summary.json`

Cleaning rules:
- remove duplicate business records
- drop rows missing the critical identifier, date, or grouping fields
- normalize embedded text fields so they are useful for later analysis
- keep suspicious numeric spikes by capping them instead of discarding the entire record
