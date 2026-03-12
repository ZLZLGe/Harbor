# Batch Acceptance Rules

Use these rules after you compute the main-part mass for each scan:

1. A scan is acceptable only if the main part's Material ID is one of:
   - `25`
   - `42`
2. The main part's mass must be less than or equal to `40000 g`.

If multiple acceptable scans have the same mass, prefer the filename that is lexicographically smaller.
