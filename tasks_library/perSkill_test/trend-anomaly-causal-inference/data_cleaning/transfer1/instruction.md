Clean the supplied ward inventory usage ledger so it can be used in downstream reporting.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer1_ward_inventory_cleaned.csv`
- `/root/transfer1_ward_inventory_summary.json`

Cleaning rules:
- remove duplicate business records
- drop rows missing the critical identifier, date, or grouping fields
- normalize embedded text fields so they are useful for later analysis
- keep suspicious numeric spikes by capping them instead of discarding the entire record
