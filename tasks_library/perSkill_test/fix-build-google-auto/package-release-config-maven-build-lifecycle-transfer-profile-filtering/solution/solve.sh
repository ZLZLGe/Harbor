#!/bin/bash
set -euo pipefail

cd /workspace/release-bulletin-service

python3 - <<'PY'
from pathlib import Path

pom = Path("pom.xml")
content = pom.read_text()

replacements = {
    "<phase>verify</phase>": "<phase>process-resources</phase>",
    "<filtering>false</filtering>": "<filtering>true</filtering>",
    "config/dev-build.properties": "config/release-build.properties",
}

for before, after in replacements.items():
    if before not in content:
        raise SystemExit(f"expected to find {before!r} in pom.xml")
    content = content.replace(before, after, 1)

pom.write_text(content)
PY

mvn -Prelease package
