#!/bin/bash
set -euo pipefail

cat > /root/transfer3_target_shortlist.csv <<'EOF'
qualname,file,harnessability,rationale
graphbundle.bundle.parse_bundle,graphbundle/bundle.py,high,top-level parser that fans out over every user-controlled line
graphbundle.bundle.parse_node_record,graphbundle/bundle.py,high,small record parser with delimiter validation and string trimming
graphbundle.schema.read_declared_type,graphbundle/schema.py,medium,prefix-based parser that rejects malformed type declarations
EOF
