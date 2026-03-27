#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from pathlib import Path


rows = [
    {
        "repo": "mailroompkg",
        "target": "mailroompkg.attachments.parse_attachment_manifest",
        "test_signal": "tests/test_attachments.py",
        "missing_case": "truncated attachment list entries",
        "priority": "P1",
    },
    {
        "repo": "quotaflags",
        "target": "quotaflags.policy.load_quota_policy",
        "test_signal": "tests/test_policy.py",
        "missing_case": "negative or reversed quota limits",
        "priority": "P1",
    },
    {
        "repo": "slugrender",
        "target": "slugrender.template.load_template_bundle",
        "test_signal": "tests/test_template.py",
        "missing_case": "missing template keys in bundle objects",
        "priority": "P1",
    },
]

output = Path("/root/transfer1_regression_queue.csv")
with output.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["repo", "target", "test_signal", "missing_case", "priority"])
    writer.writeheader()
    writer.writerows(rows)
PY
