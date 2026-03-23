Clean the supplied applicant intake roster so it can be used in downstream reporting.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer3_applicant_intake_cleaned.csv`
- `/root/transfer3_applicant_intake_summary.json`

Cleaning rules:
- remove duplicate business records
- drop rows missing the critical identifier, date, or grouping fields
- normalize embedded text fields so they are useful for later analysis
- keep suspicious numeric spikes by capping them instead of discarding the entire record
