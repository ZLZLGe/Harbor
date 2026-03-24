#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import hashlib
import json
import os
import shutil
from pathlib import Path

root = Path(os.environ.get("SEMINAR_ROOT", "/root/seminar_drop"))
inbox = root / "inbox"
organized = root / "organized"
reports = root / "reports"

file_to_category = {
    "archive_box_01.pdf": "causal_inference",
    "archive_box_02.pdf": "field_robotics",
    "archive_box_03.pdf": "climate_transition",
    "archive_box_04.pdf": "graph_learning",
    "archive_box_05.pdf": "causal_inference",
    "archive_box_06.pdf": "field_robotics",
    "archive_box_07.pdf": "climate_transition",
    "archive_box_08.pdf": "graph_learning",
    "archive_box_09.docx": "causal_inference",
    "archive_box_10.docx": "graph_learning",
    "archive_box_11.pptx": "field_robotics",
    "archive_box_12.pptx": "climate_transition",
}

reports.mkdir(parents=True, exist_ok=True)
organized.mkdir(parents=True, exist_ok=True)

manifest = []
for file_name in sorted(file_to_category):
    category = file_to_category[file_name]
    source_path = inbox / file_name
    destination_dir = organized / category
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / file_name

    shutil.move(str(source_path), str(destination_path))
    sha256 = hashlib.sha256(destination_path.read_bytes()).hexdigest()
    manifest.append(
        {
            "file_name": file_name,
            "category": category,
            "source": str(source_path),
            "destination": str(destination_path),
            "sha256": sha256,
        }
    )

manifest_path = reports / "placement_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
