#!/bin/bash
set -euo pipefail

PROJECT_DIR=/workspace/build-metadata-service
POM_FILE="$PROJECT_DIR/pom.xml"

python3 - <<'PY'
from pathlib import Path
import re

pom_path = Path("/workspace/build-metadata-service/pom.xml")
content = pom_path.read_text()
updated, count = re.subn(
    r"(<execution>\s*<id>generate-build-metadata</id>\s*<phase>)verify(</phase>)",
    r"\1generate-sources\2",
    content,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit("failed to update generate-build-metadata phase")
pom_path.write_text(updated)
PY

cd "$PROJECT_DIR"
mvn verify
