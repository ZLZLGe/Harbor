import json
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
    const_path = root / spec["const_file"]
    if not const_path.exists():
        raise SystemExit(f"missing const file: {const_path}")
    content = const_path.read_text(encoding="utf-8")
    for token in spec.get("forbidden_substrings", []):
        if token in content:
            raise SystemExit(f"forbidden token present: {token}")

    arch_line, values = parse_const_file(const_path)
    if arch_line != spec["arch_line"]:
        raise SystemExit(f"expected arch line {spec['arch_line']!r}, got {arch_line!r}")

    expected = spec["constants"]
    for key, expected_value in expected.items():
        actual = values.get(key)
        if actual != expected_value:
            raise SystemExit(f"{key} expected {expected_value}, got {actual}")

    print(f"validated {const_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
