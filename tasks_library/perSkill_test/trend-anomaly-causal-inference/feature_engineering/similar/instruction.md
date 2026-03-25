Turn the member survey table into a modeling-ready feature table.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/similar_member_features.csv`
- `/root/similar_member_features_summary.json`

Requirements:
- keep the original member identifier column
- convert the remaining columns into numeric modeling features
- remove columns that are constant and carry no information
- keep the final table free of null values
