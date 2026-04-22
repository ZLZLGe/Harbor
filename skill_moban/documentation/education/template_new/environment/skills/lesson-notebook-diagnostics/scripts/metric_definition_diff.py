from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import nbformat
import yaml


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: metric_definition_diff.py <notebook-path> <manifest-path>",
            file=sys.stderr,
        )
        return 2

    notebook_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])

    workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
    metrics_doc = yaml.safe_load(
        (workspace_root / "metric_definitions.yaml").read_text(encoding="utf-8")
    )
    valid_metrics = {item["name"] for item in metrics_doc["metrics"]}

    nb = nbformat.read(notebook_path, as_version=4)
    notebook_text = "\n".join(cell.source for cell in nb.cells)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_metrics = [item["name"] for item in manifest.get("key_metrics", [])]

    report = {
        "valid_metrics": sorted(valid_metrics),
        "manifest_metrics": manifest_metrics,
        "manifest_unknown_metrics": [name for name in manifest_metrics if name not in valid_metrics],
        "notebook_mentions": [name for name in valid_metrics if name in notebook_text],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
