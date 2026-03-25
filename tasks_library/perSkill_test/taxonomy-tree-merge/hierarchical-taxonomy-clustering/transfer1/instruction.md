Three grocery merchants exported their browse paths for a small promo reporting bundle. The source files are in `/root/data/`:

- `grocer_a.csv`
- `grocer_b.jsonl`
- `grocer_c.tsv`

The merchants describe the same product families with different hierarchy wording. Build one shared four-level taxonomy for promotion reporting and write the outputs to `/root/output/`.

Required outputs:

1. `transfer1_grocery_rollup.csv`
   - columns: `source`, `item_path`, `unified_department`, `unified_aisle`, `unified_shelf`, `unified_leaf`
   - include every source record exactly once

2. `transfer1_taxonomy_nodes.json`
   - JSON array of unique unified taxonomy paths
   - each item must contain `unified_department`, `unified_aisle`, `unified_shelf`, `unified_leaf`

Rules:

- semantically equivalent grocery paths must land on the same unified path
- keep category names stable and reusable across merchants
- the JSON node list must contain each unified path only once
- do not drop any source rows
