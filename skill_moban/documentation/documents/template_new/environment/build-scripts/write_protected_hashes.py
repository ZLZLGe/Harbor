from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    base = Path("/app")
    protected = {
        "input_files": {
            "vendor_addendum_redline.docx": sha256_file(base / "vendor_addendum_redline.docx"),
            "review_decisions.json": sha256_file(base / "review_decisions.json"),
        },
        "skill_files": {},
    }

    root = Path("/home/appuser/.codex/skills")
    if root.exists():
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = str(path.relative_to(root))
            protected["skill_files"][rel] = sha256_file(path)

    out_dir = Path("/opt/documents-task")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "protected_hashes.json").write_text(json.dumps(protected, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
