#!/usr/bin/env python3
from __future__ import annotations

import subprocess


def main() -> None:
    subprocess.run(
        ["python3", "-m", "marketplace_snapshot.cli", "build"],
        check=True,
    )
    subprocess.run(
        ["submit_marketplace_bundle"],
        check=True,
    )


if __name__ == "__main__":
    main()
