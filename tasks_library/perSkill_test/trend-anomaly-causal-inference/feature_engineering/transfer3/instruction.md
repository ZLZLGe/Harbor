Turn the clinic intake table into a modeling-ready feature table.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer3_intake_features.csv`
- `/root/transfer3_intake_features_summary.json`

Requirements:
- keep the patient identifier column
- convert the remaining columns into numeric features
- remove constant fields with no modeling value
- leave the final table free of null values
