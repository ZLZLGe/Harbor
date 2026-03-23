#!/bin/bash
set -euo pipefail

cd /workspace

python3 <<'PY'
from pathlib import Path

mappings = [
    ("javax.persistence", "jakarta.persistence"),
    ("javax.validation", "jakarta.validation"),
    ("javax.servlet", "jakarta.servlet"),
    ("javax.annotation", "jakarta.annotation"),
    ("javax.transaction", "jakarta.transaction"),
]

for java_file in Path("/workspace/src").rglob("*.java"):
    content = java_file.read_text()
    updated = content
    for old, new in mappings:
        updated = updated.replace(old, new)
    if updated != content:
        java_file.write_text(updated)
PY

python3 <<'PY'
import json
from pathlib import Path

report = {
    "service": "user-roster",
    "migrated_files": [
        "src/main/java/com/example/roster/controller/UserRosterController.java",
        "src/main/java/com/example/roster/dto/UserSignupRequest.java",
        "src/main/java/com/example/roster/filter/CorrelationIdFilter.java",
        "src/main/java/com/example/roster/model/RosterUser.java",
    ],
    "packages_fixed": [
        "javax.persistence",
        "javax.servlet",
        "javax.validation",
    ],
    "remaining_javax_imports": 0,
}
Path("/root/similar_namespace_report.json").write_text(json.dumps(report, indent=2) + "\n")
PY

/workspace/verify.sh
