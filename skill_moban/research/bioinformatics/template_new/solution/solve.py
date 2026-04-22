#!/usr/bin/env python3

import shutil
import subprocess
from pathlib import Path


def main() -> None:
    solution_dir = Path(__file__).resolve().parent
    fixed = solution_dir / "fixed_run_analysis.py"
    target = Path("/root/environment/pipeline/run_analysis.py")
    shutil.copyfile(fixed, target)
    subprocess.run(
        ["python", str(target), "--output", "/root/answer"],
        check=True,
    )


if __name__ == "__main__":
    main()
