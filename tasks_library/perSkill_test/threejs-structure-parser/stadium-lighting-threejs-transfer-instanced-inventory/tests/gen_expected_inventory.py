import json
from pathlib import Path


if __name__ == "__main__":
    source = Path("/root/expected_inventory.json")
    target = Path("/logs/verifier/outputs/expected_inventory_snapshot.json")
    if source.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
