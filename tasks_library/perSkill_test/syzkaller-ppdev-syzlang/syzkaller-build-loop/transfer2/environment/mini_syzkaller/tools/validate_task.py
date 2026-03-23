import json
import re
from pathlib import Path


def parse_const_file(path: Path) -> tuple[str | None, dict[str, int]]:
    arch_line = None
    values: dict[str, int] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("arches"):
            arch_line = line
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = int(value.strip(), 0)
    return arch_line, values


def main() -> int:
    root = Path("/opt/syzkaller")
    spec = json.loads((root / "task_spec.json").read_text(encoding="utf-8"))
    text_path = root / spec["text_file"]
    const_path = root / spec["const_file"]
    text = text_path.read_text(encoding="utf-8")
    for rule in spec["required_regexes"]:
        if not re.search(rule["pattern"], text, flags=re.MULTILINE):
            raise SystemExit(rule["message"])

    arch_line, values = parse_const_file(const_path)
    if arch_line != spec["arch_line"]:
        raise SystemExit(f"expected arch line {spec['arch_line']!r}, got {arch_line!r}")
    for key, expected_value in spec["constants"].items():
        actual = values.get(key)
        if actual != expected_value:
            raise SystemExit(f"{key} expected {expected_value}, got {actual}")

    print("validated task package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
