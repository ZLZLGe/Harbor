#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from digest_oracle import APP_ROOT, build_expected_digest, render_markdown


def main() -> None:
    output_dir = APP_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = build_expected_digest()
    (output_dir / "feed_digest.json").write_text(
        json.dumps(digest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "feed_digest.md").write_text(render_markdown(digest), encoding="utf-8")


if __name__ == "__main__":
    main()
