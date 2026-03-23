Turn the donor outreach table into a modeling-ready feature table.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer1_donor_features.csv`
- `/root/transfer1_donor_features_summary.json`

Requirements:
- keep the donor identifier column
- transform the remaining columns into numeric features
- remove constant columns that do not vary across donors
- leave the final table free of null values
