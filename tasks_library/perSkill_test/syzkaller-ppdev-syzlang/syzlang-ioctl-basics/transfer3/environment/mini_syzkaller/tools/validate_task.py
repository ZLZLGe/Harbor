import json
import re
import sys
from pathlib import Path


def main() -> int:
    root = Path("/opt/syzkaller")
    spec = json.loads((root / "task_spec.json").read_text(encoding="utf-8"))
    target = root / spec["target_file"]
    if not target.exists():
        raise SystemExit(f"missing target file: {target}")

    content = target.read_text(encoding="utf-8")
    for token in spec.get("forbidden_substrings", []):
        if token in content:
            raise SystemExit(f"forbidden token present: {token}")

    for rule in spec.get("required_regexes", []):
        if not re.search(rule["pattern"], content, flags=re.MULTILINE):
            raise SystemExit(rule["message"])

    print(f"validated {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
