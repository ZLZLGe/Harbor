Read `/root/compound_properties_table.dat`. It is a two-page document containing one table with these columns:

- `Compound`
- `MolecularWeight`
- `XLogP`
- `HBD`
- `HBA`
- `TPSA`

Use every row in that table as the compound pool.

For the five numeric columns, compute min-max normalized values across the full pool with:

`normalized_value = (value - column_min) / (column_max - column_min)`

Then, for each target compound below, compute Euclidean distance over those five normalized columns against every other compound in the pool:

- `Acetaminophen`, `top_k = 3`
- `Ibuprofen`, `top_k = 4`

Rules:

- Exclude the target compound itself from its own neighbor list.
- Sort by ascending distance.
- Break ties by compound name in alphabetical order.
- Round each reported distance to 4 decimal places.
- Do not use any external data source; only use the table in the provided document.

Write `/root/workspace/compound_neighbors.json` with this exact JSON shape:

```json
{
  "source_document": "/root/compound_properties_table.dat",
  "distance_metric": "euclidean_on_minmax_normalized_columns",
  "normalized_columns": ["molecular_weight", "xlogp", "hbd", "hba", "tpsa"],
  "extracted_compound_count": 11,
  "queries": [
    {
      "target": "Acetaminophen",
      "top_k": 3,
      "neighbors": [
        {"compound": "example", "distance": 0.1234}
      ]
    }
  ]
}
```
