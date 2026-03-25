#!/usr/bin/env python3

import re
import subprocess
import sys
import tempfile
from pathlib import Path

CONST_FILE = Path("/opt/syzkaller/sys/linux/dev_demo_compat.txt.const")
HEADER_ROOT = Path("/opt/task-assets/mock-uapi")
ARCH_FLAGS = {
    "amd64": "-m64",
    "386": "-m32",
}
SYMBOLS = [
    "DEMO_IOCTL_PEEK",
    "DEMO_IOCTL_POKE",
    "DEMO_IOCTL_XACT",
    "DEMO_IOCTL_PING",
    "DEMO_MODE_STRICT",
    "DEMO_MODE_BULK",
    "DEMO_FLAG_SHARED",
    "DEMO_FLAG_TRACE",
]


def parse_const_file():
    values = {}
    for raw in CONST_FILE.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("arches"):
            continue
        if "=" not in line:
            continue
        name, rhs = [part.strip() for part in line.split("=", 1)]
        if ":" not in rhs:
            values[name] = int(rhs, 0)
            continue
        per_arch = {}
        for chunk in rhs.split(","):
            arch, value = [part.strip() for part in chunk.split(":", 1)]
            per_arch[arch] = int(value, 0)
        values[name] = per_arch
    return values


def resolve_value(values, name, arch):
    value = values[name]
    if isinstance(value, dict):
        return value[arch]
    return value


def compile_expected(arch):
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "print_demo_consts.c"
        binary = Path(tmpdir) / "print_demo_consts"
        src.write_text(
            "\n".join(
                [
                    "#include <stdio.h>",
                    "#include <linux/dev_demo_compat.h>",
                    "int main(void) {",
                    '    printf("DEMO_IOCTL_PEEK=%llu\\n", (unsigned long long)DEMO_IOCTL_PEEK);',
                    '    printf("DEMO_IOCTL_POKE=%llu\\n", (unsigned long long)DEMO_IOCTL_POKE);',
                    '    printf("DEMO_IOCTL_XACT=%llu\\n", (unsigned long long)DEMO_IOCTL_XACT);',
                    '    printf("DEMO_IOCTL_PING=%llu\\n", (unsigned long long)DEMO_IOCTL_PING);',
                    '    printf("DEMO_MODE_STRICT=%llu\\n", (unsigned long long)DEMO_MODE_STRICT);',
                    '    printf("DEMO_MODE_BULK=%llu\\n", (unsigned long long)DEMO_MODE_BULK);',
                    '    printf("DEMO_FLAG_SHARED=%llu\\n", (unsigned long long)DEMO_FLAG_SHARED);',
                    '    printf("DEMO_FLAG_TRACE=%llu\\n", (unsigned long long)DEMO_FLAG_TRACE);',
                    "    return 0;",
                    "}",
                ]
            )
            + "\n"
        )
        result = subprocess.run(
            ["gcc", ARCH_FLAGS[arch], "-I", str(HEADER_ROOT), str(src), "-o", str(binary)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stdout + "\n" + result.stderr)
        output = subprocess.check_output([str(binary)], text=True)
    expected = {}
    for line in output.splitlines():
        name, value = line.strip().split("=", 1)
        expected[name] = int(value, 0)
    return expected


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ARCH_FLAGS:
        print("usage: verify_demo_compat.py <amd64|386>", file=sys.stderr)
        return 2
    arch = sys.argv[1]
    if not CONST_FILE.exists():
        print(f"missing {CONST_FILE}", file=sys.stderr)
        return 1
    content = CONST_FILE.read_text()
    if not re.search(r"^arches\s*=\s*amd64,\s*386\s*$", content, re.M):
        print("arches line must be exactly: arches = amd64, 386", file=sys.stderr)
        return 1

    values = parse_const_file()
    expected = compile_expected(arch)
    for name in SYMBOLS:
        if name not in values:
            print(f"missing constant: {name}", file=sys.stderr)
            return 1
        actual = resolve_value(values, name, arch)
        if actual != expected[name]:
            print(
                f"{arch}: {name} mismatch, expected {expected[name]}, got {actual}",
                file=sys.stderr,
            )
            return 1
    print(f"{arch}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
