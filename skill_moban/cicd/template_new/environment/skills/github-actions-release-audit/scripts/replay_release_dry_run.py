from __future__ import annotations

import argparse
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default="/app/workspace")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    subprocess.run(["make", "-C", args.workspace, "clean"], check=True)
    subprocess.run(["make", "-C", args.workspace, "release-dry-run"], check=True)


if __name__ == "__main__":
    main()
