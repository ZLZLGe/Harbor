Turn the rider profile table into a modeling-ready feature table.

Input file:
- `/root/data/raw.csv`

Save:
- `/root/transfer2_rider_features.csv`
- `/root/transfer2_rider_features_summary.json`

Requirements:
- keep the rider identifier column
- convert the remaining columns into numeric features
- drop constant columns with no usable variance
- leave the final feature table free of null values
