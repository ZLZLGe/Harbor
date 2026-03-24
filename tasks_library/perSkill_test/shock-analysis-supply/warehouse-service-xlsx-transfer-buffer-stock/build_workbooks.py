#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
ASSETS = {
    "template": TASK_DIR / "environment" / "warehouse-buffer-template.xlsx",
    "answer": TASK_DIR / "solution" / "answer-warehouse-buffer-stock.xlsx",
}


def export_assets(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset_path in ASSETS.values():
        if not asset_path.exists():
            raise FileNotFoundError(f"Missing workbook asset: {asset_path}")
        target_path = output_dir / asset_path.name
        shutil.copy2(asset_path, target_path)
        print(target_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the checked-in workbook assets for this task."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=TASK_DIR / "_exported_workbooks",
        help="Directory that will receive copies of the committed workbook assets.",
    )
    args = parser.parse_args()
    export_assets(args.output_dir)


if __name__ == "__main__":
    main()
