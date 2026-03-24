#!/bin/bash
set -euo pipefail

REPO_ROOT=/opt/build-triage-helper
FAILED_COPY=$REPO_ROOT/workspace/failed_copy
ANALYSIS_DIR=$REPO_ROOT/workspace/analysis
HELPER_ROOT=/opt/build-triage-helper-bootstrap

mkdir -p "$ANALYSIS_DIR"
cat <<'EOF' > "$ANALYSIS_DIR/plan.txt"
The failed copy cannot satisfy the reproduction script for three reasons:
1. `triage_app/__init__.py` exports the wrong symbol.
2. `triage_app/engine.py` sorts services incorrectly and writes `/n` instead of real newlines.
3. `pyproject.toml` points the console script at `triage_app.engine:run`, which does not exist.

Plan:
- implement `tools/fetch_patch_bundle.py` to turn the bundle templates into unified diffs;
- bootstrap a sibling Python helper project for the script dependency;
- run the helper script, apply the generated diffs, and verify with `run_repro.sh`.
EOF

mkdir -p "$HELPER_ROOT"
cd "$HELPER_ROOT"
if [ ! -f pyproject.toml ]; then
  uv init --python 3.11
fi
uv add pyyaml==6.0.2

cd "$REPO_ROOT"
mkdir -p tools
cat <<'PY' > tools/fetch_patch_bundle.py
from __future__ import annotations

import argparse
import difflib
import subprocess
from pathlib import Path

import yaml


def build_patch(
    repo_root: Path,
    target_relpath: str,
    template_relpath: str,
    patch_dir: Path,
    index: int,
) -> Path:
    target_path = repo_root / target_relpath
    template_path = repo_root / "patch_bundle" / template_relpath

    before = target_path.read_text(encoding="utf-8").splitlines(keepends=True)
    after = template_path.read_text(encoding="utf-8").splitlines(keepends=True)

    diff_text = "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile=target_relpath,
            tofile=target_relpath,
        )
    )
    patch_path = patch_dir / f"bundle_patch_{index}.diff"
    patch_path.write_text(diff_text, encoding="utf-8")
    return patch_path


def apply_patch(repo_root: Path, patch_path: Path) -> None:
    subprocess.run(
        ["patch", "-p0", "-i", str(patch_path)],
        cwd=repo_root,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parent.parent,
        type=Path,
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    manifest_path = repo_root / "patch_bundle" / "bundle.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    patch_dir = repo_root / manifest["patch_dir"]
    patch_dir.mkdir(parents=True, exist_ok=True)

    patch_paths = []
    for index, item in enumerate(manifest["targets"]):
        patch_paths.append(
            build_patch(
                repo_root=repo_root,
                target_relpath=item["target"],
                template_relpath=item["template"],
                patch_dir=patch_dir,
                index=index,
            )
        )

    if args.apply:
        for patch_path in patch_paths:
            apply_patch(repo_root, patch_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

cd "$HELPER_ROOT"
uv run python /opt/build-triage-helper/tools/fetch_patch_bundle.py --apply

bash /opt/build-triage-helper/run_repro.sh
