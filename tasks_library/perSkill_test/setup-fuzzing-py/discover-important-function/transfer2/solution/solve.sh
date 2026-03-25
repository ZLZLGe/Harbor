#!/bin/bash
set -euo pipefail

cat > /root/transfer2_oracle_map.md <<'EOF'
# mergebotconfig oracle map

- `parse_rule_block`:
  - inferred oracle: duplicate environment keys must raise `ValueError`
  - evidence: `test_parse_rule_block_rejects_duplicate_env_keys`

- `parse_schedule`:
  - inferred oracle: invalid minute values must raise `ValueError`
  - evidence: `test_parse_schedule_rejects_invalid_minute`

- `load_policy_document`:
  - inferred oracle: blank rule groups are ignored while the remaining rule order is preserved
  - evidence: `test_load_policy_document_ignores_blank_rules_and_preserves_order`
EOF
