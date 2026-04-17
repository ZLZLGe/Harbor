#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run(script_name: str) -> int:
    print(f"=== {script_name} ===")
    completed = subprocess.run([sys.executable, str(SCRIPT_DIR / script_name)], check=False)
    print()
    return completed.returncode


exit_code = 0
for script in ["audit_screening.py", "audit_bibliography.py", "audit_summary.py"]:
    exit_code = exit_code or run(script)

raise SystemExit(exit_code)
