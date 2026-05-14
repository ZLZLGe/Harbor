from __future__ import annotations

import argparse
import os
from pathlib import Path

from batch_runner import build_outputs, write_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the renewal billing batch.")
    parser.add_argument("--data-root", default=os.environ.get("TASK_DATA_ROOT", "/root/data"))
    parser.add_argument("--output-root", default=os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, summary = build_outputs(Path(args.data_root))
    write_outputs(rows, summary, Path(args.output_root))


if __name__ == "__main__":
    main()
