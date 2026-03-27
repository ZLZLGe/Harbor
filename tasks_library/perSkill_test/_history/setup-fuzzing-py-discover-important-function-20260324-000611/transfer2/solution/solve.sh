#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path


lines = [
    "rank\tpath\tsymbol\trisk_kind\ttest_signal",
    "1\topssuite/ingest/http_payload.py\topssuite.ingest.http_payload.parse_ingest_request\tjson\ttests/test_ingest.py",
    "2\topssuite/ingest/batch_loader.py\topssuite.ingest.batch_loader.load_batch_manifest\tjson\ttests/test_ingest.py",
    "3\topssuite/auth/token_file.py\topssuite.auth.token_file.decode_token_blob\tbinary\ttests/test_auth.py",
    "4\topssuite/export/archive_index.py\topssuite.export.archive_index.load_archive_index\tindex\ttests/test_export.py",
    "5\topssuite/policies/yaml_rules.py\topssuite.policies.yaml_rules.parse_rules_doc\tyaml\ttests/test_policies.py",
    "6\topssuite/templates/route_template.py\topssuite.templates.route_template.parse_route_template\ttemplate\ttests/test_templates.py",
]

Path("/root/transfer2_boundary_map.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
