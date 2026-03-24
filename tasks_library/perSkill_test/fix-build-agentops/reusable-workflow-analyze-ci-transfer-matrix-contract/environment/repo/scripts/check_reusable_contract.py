#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CALLER_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "service-analysis.yml"
REUSABLE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "reusable-service-analysis.yml"


def extract_matrix_entries(lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s+- service:\s*([A-Za-z0-9_-]+)\s*$", line)
        if not match:
            continue
        service = match.group(1)
        if index + 1 >= len(lines):
            raise ValueError("matrix entry is missing python-version")
        version_line = lines[index + 1]
        version_match = re.match(r'^\s+python-version:\s*"?(.*?)"?\s*$', version_line)
        if not version_match:
            raise ValueError("matrix entry is missing python-version")
        entries.append((service, version_match.group(1)))
    if not entries:
        raise ValueError("no matrix entries found in caller workflow")
    return entries


def extract_with_keys(lines: list[str]) -> list[str]:
    in_with = False
    keys: list[str] = []
    for line in lines:
        if re.match(r"^\s{4}with:\s*$", line):
            in_with = True
            continue
        if not in_with:
            continue
        key_match = re.match(r"^\s{6}([A-Za-z0-9_-]+):\s*", line)
        if key_match:
            keys.append(key_match.group(1))
            continue
        if line.strip() == "":
            continue
        if re.match(r"^\s{2}[A-Za-z0-9_-]+:\s*$", line) or re.match(r"^\s{4}[A-Za-z0-9_-]+:\s*$", line):
            break
    if not keys:
        raise ValueError("no with: keys found in caller workflow")
    return keys


def extract_reusable_inputs(lines: list[str]) -> list[str]:
    in_workflow_call = False
    in_inputs = False
    inputs: list[str] = []
    for line in lines:
        if re.match(r"^\s{2}workflow_call:\s*$", line):
            in_workflow_call = True
            continue
        if not in_workflow_call:
            continue
        if re.match(r"^\s{4}inputs:\s*$", line):
            in_inputs = True
            continue
        if in_inputs:
            key_match = re.match(r"^\s{6}([A-Za-z0-9_-]+):\s*$", line)
            if key_match:
                inputs.append(key_match.group(1))
                continue
            if line.strip() == "":
                continue
            if re.match(r"^\s{2}[A-Za-z0-9_-]+:\s*$", line):
                break
    if not inputs:
        raise ValueError("no reusable workflow inputs found")
    return inputs


def main() -> int:
    caller_lines = CALLER_WORKFLOW.read_text().splitlines()
    reusable_lines = REUSABLE_WORKFLOW.read_text().splitlines()

    matrix_entries = extract_matrix_entries(caller_lines)
    with_keys = extract_with_keys(caller_lines)
    reusable_inputs = extract_reusable_inputs(reusable_lines)

    missing_keys = [key for key in with_keys if key not in reusable_inputs]

    if missing_keys:
        for service, version in matrix_entries:
            print(
                f"ERROR analyze-service ({service}, {version}): "
                f"{CALLER_WORKFLOW.relative_to(REPO_ROOT)} passes "
                f"{', '.join(missing_keys)} but "
                f"{REUSABLE_WORKFLOW.relative_to(REPO_ROOT)} does not declare it under workflow_call.inputs."
            )
        print("BLOCKED publish-analysis-summary: waiting for analyze-service matrix to succeed.")
        return 1

    for service, version in matrix_entries:
        print(f"PASS analyze-service ({service}, {version}): reusable workflow contract satisfied.")
    print("PASS publish-analysis-summary: all matrix jobs satisfied the reusable workflow contract.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"contract check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
