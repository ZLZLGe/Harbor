#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from common import infer_slide_manifest_from_html


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/app"))


def resolve_task_path(path_str: str) -> Path:
    if path_str.startswith("/app/"):
        return TASK_ROOT / path_str.removeprefix("/app/")
    if path_str == "/app":
        return TASK_ROOT
    return Path(path_str)


def main() -> None:
    failures: list[str] = []
    manifest = infer_slide_manifest_from_html()
    for slide in manifest:
        if not slide["title"].strip():
            failures.append(f"slide {slide['index']} is missing a title")
        if not slide["source_refs"]:
            failures.append(f"slide {slide['index']} is missing machine-readable source refs")
            continue
        for ref in slide["source_refs"]:
            if not ref.startswith("/app/workspace/"):
                failures.append(f"slide {slide['index']} has invalid source ref {ref!r}")
            elif not resolve_task_path(ref).exists():
                failures.append(f"slide {slide['index']} references missing source {ref}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)

    print("OK: source trace markers look complete")


if __name__ == "__main__":
    main()
