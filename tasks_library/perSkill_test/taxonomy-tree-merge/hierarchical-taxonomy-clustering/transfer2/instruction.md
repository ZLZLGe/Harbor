Three pet-subscription suppliers exported category paths for recurring bundle routing. The input files are in `/root/data/`:

- `supplier_one.csv`
- `supplier_two.json`
- `supplier_three.txt`

The suppliers describe the same bundle families with different hierarchy labels. Build one shared three-level fulfillment taxonomy and write the outputs to `/root/output/`.

Required outputs:

1. `transfer2_bundle_assignments.json`
   - JSON array
   - each item must contain `source`, `category_path`, `unified_group`, `unified_family`, `unified_cluster`
   - include every source record exactly once

2. `transfer2_cluster_summary.csv`
   - columns: `unified_group`, `unified_family`, `unified_cluster`, `source_count`, `record_count`
   - one row per unique unified cluster

Rules:

- semantically equivalent bundle paths must land on the same unified cluster
- keep the shared taxonomy consistent across all suppliers
- the summary file must aggregate the assignment output rather than invent extra clusters
