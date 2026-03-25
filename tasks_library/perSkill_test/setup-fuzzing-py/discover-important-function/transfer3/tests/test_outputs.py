import csv
from pathlib import Path


with Path("/root/transfer3_target_shortlist.csv").open() as handle:
    rows = list(csv.DictReader(handle))

assert rows[0]["qualname"] == "graphbundle.bundle.parse_bundle"
assert rows[0]["harnessability"] == "high"
assert any(row["qualname"] == "graphbundle.bundle.parse_node_record" for row in rows)
assert any(row["qualname"] == "graphbundle.schema.read_declared_type" for row in rows)
