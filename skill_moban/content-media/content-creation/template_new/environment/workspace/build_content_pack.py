#!/usr/bin/env python3

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args()


def main() -> int:
    parse_args()
    raise SystemExit("build_content_pack.py is incomplete and must be finished for this task")


if __name__ == "__main__":
    raise SystemExit(main())
