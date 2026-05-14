from __future__ import annotations

import json
import sys
from pathlib import Path


DATA_ROOT = Path("/root/data")
SCRIPT_ROOT = Path("/root/.codex/skills/billing-automation/scripts")


def load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: inspect_subscription.py SUB-1007", file=sys.stderr)
        return 1

    subscription_id = argv[1]
    subscriptions = {row["subscription_id"]: row for row in load_rows(DATA_ROOT / "subscription_snapshot.ndjson")}
    invoices = {row["subscription_id"]: row for row in load_rows(DATA_ROOT / "invoice_snapshot.ndjson")}

    if subscription_id not in subscriptions:
        print(f"unknown subscription: {subscription_id}", file=sys.stderr)
        return 1

    print(json.dumps({"subscription": subscriptions[subscription_id], "invoice": invoices[subscription_id]}, indent=2, sort_keys=True))
    print()
    print("Candidate batch record:")
    import subprocess

    proc = subprocess.run(
        ["python3", str(SCRIPT_ROOT / "batch_audit.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if f"\"subscription_id\": \"{subscription_id}\"" in line:
            print(line)
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
