#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import subprocess
import tempfile
from pathlib import Path

MANIFEST = Path("/opt/task-assets/compat_manifest.json")
HEADER_ROOT = Path("/opt/task-assets/mock-uapi")
OUTPUT = Path("/opt/syzkaller/sys/linux/dev_demo_compat.txt.const")
ARCH_FLAGS = {
    "amd64": "-m64",
    "386": "-m32",
}


def load_manifest():
    return json.loads(MANIFEST.read_text())


def compile_values(symbols, arch):
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "extract_consts.c"
        binary = Path(tmpdir) / "extract_consts"
        body = [
            "#include <stdio.h>",
            "#include <linux/dev_demo_compat.h>",
            "int main(void) {",
        ]
        for symbol in symbols:
            body.append(f'    printf("{symbol}=%llu\\n", (unsigned long long){symbol});')
        body.extend(
            [
                "    return 0;",
                "}",
            ]
        )
        src.write_text("\n".join(body) + "\n")
        subprocess.run(
            ["gcc", ARCH_FLAGS[arch], "-I", str(HEADER_ROOT), str(src), "-o", str(binary)],
            check=True,
            capture_output=True,
            text=True,
        )
        output = subprocess.check_output([str(binary)], text=True)
    values = {}
    for line in output.splitlines():
        name, value = line.split("=", 1)
        values[name] = int(value, 0)
    return values


manifest = load_manifest()
symbols = [item["name"] for item in manifest["symbols"]]
amd64 = compile_values(symbols, "amd64")
i386 = compile_values(symbols, "386")

lines = [
    "# Corrected compat ioctl constants for amd64 and 386",
    "arches = amd64, 386",
    "",
]

for item in manifest["symbols"]:
    name = item["name"]
    amd64_value = amd64[name]
    i386_value = i386[name]
    if item.get("arch_sensitive"):
        lines.append(f"{name} = amd64:{amd64_value}, 386:{i386_value}")
    elif amd64_value == i386_value:
        lines.append(f"{name} = {amd64_value}")
    else:
        lines.append(f"{name} = amd64:{amd64_value}, 386:{i386_value}")

OUTPUT.write_text("\n".join(lines) + "\n")
PY

python3 /opt/task-assets/verify_demo_compat.py amd64
python3 /opt/task-assets/verify_demo_compat.py 386
