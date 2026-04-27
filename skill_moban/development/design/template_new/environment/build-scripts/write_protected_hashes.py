from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOTS = [
    Path("/root/data"),
    Path("/services/frontend-slides-api"),
    Path("/root/.codex/skills"),
    Path("/logs/agent/skills"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest: dict[str, str] = {}
for root in ROOTS:
    if not root.exists():
        continue
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.name == "protected_hashes.json":
            continue
        manifest[str(path)] = sha256(path)

Path("/opt/frontend-slides-task/protected_hashes.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
