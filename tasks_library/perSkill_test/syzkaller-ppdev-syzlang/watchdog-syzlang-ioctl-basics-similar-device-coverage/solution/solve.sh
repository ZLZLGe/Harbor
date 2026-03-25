#!/bin/bash
set -euo pipefail

cd /opt/syzkaller/sys/linux

python3 <<'PY'
import re
from pathlib import Path

EXCERPT = Path("/task-assets/watchdog_uapi_excerpt.h").read_text()

IOCTL_RE = re.compile(
    r"#define\s+(WDIOC_[A-Z0-9_]+)\s+_(IO|IOR|IOW|IOWR)\(WATCHDOG_IOCTL_BASE,\s*([0-9]+),\s*([^)]+)\)"
)
FLAG_RE = re.compile(r"#define\s+((?:WDIOF|WDIOS)_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+|[0-9]+)")

ioctls = []
for name, encoding, nr, arg_type in IOCTL_RE.findall(EXCERPT):
    ioctls.append(
        {
            "name": name,
            "encoding": "_" + encoding,
            "nr": int(nr),
            "arg_type": arg_type.strip(),
        }
    )

flags = {}
for name, value in FLAG_RE.findall(EXCERPT):
    flags[name] = int(value, 0)

SIZEOF = {
    "int": 4,
    "struct watchdog_info": 40,
}

SIGNATURES = {
    "WDIOC_GETSUPPORT": ("out", "watchdog_info"),
    "WDIOC_GETSTATUS": ("out", "int32"),
    "WDIOC_GETBOOTSTATUS": ("out", "int32"),
    "WDIOC_GETTEMP": ("out", "int32"),
    "WDIOC_SETOPTIONS": ("in", "flags[watchdog_set_options, int32]"),
    "WDIOC_KEEPALIVE": None,
    "WDIOC_SETTIMEOUT": ("inout", "int32"),
    "WDIOC_GETTIMEOUT": ("out", "int32"),
    "WDIOC_SETPRETIMEOUT": ("inout", "int32"),
    "WDIOC_GETPRETIMEOUT": ("out", "int32"),
    "WDIOC_GETTIMELEFT": ("out", "int32"),
}

STATUS_FLAGS = [
    "WDIOF_OVERHEAT",
    "WDIOF_FANFAULT",
    "WDIOF_EXTERN1",
    "WDIOF_EXTERN2",
    "WDIOF_POWERUNDER",
    "WDIOF_CARDRESET",
    "WDIOF_POWEROVER",
    "WDIOF_SETTIMEOUT",
    "WDIOF_MAGICCLOSE",
    "WDIOF_PRETIMEOUT",
    "WDIOF_ALARMONLY",
    "WDIOF_KEEPALIVEPING",
]

SET_OPTIONS = [
    "WDIOS_DISABLECARD",
    "WDIOS_ENABLECARD",
    "WDIOS_TEMPPANIC",
]

def encode_ioctl(op, nr, size):
    base = (ord("W") << 8) | nr
    if op == "_IO":
        return base
    if op == "_IOR":
        return 0x80000000 | (size << 16) | base
    if op == "_IOW":
        return 0x40000000 | (size << 16) | base
    if op == "_IOWR":
        return 0xC0000000 | (size << 16) | base
    raise ValueError(op)


txt_lines = [
    "include <linux/watchdog.h>",
    "",
    "resource fd_watchdog[fd]",
    "",
    'syz_open_dev$watchdog(dev ptr[in, string["/dev/watchdog#"]], id intptr, flags flags[open_flags]) fd_watchdog',
    "",
]

for ioctl in ioctls:
    signature = SIGNATURES[ioctl["name"]]
    if signature is None:
        txt_lines.append(f"ioctl${ioctl['name']}(fd fd_watchdog, cmd const[{ioctl['name']}])")
        continue
    direction, ty = signature
    txt_lines.append(
        f"ioctl${ioctl['name']}(fd fd_watchdog, cmd const[{ioctl['name']}], arg ptr[{direction}, {ty}])"
    )

txt_lines.extend(
    [
        "",
        "watchdog_info {",
        "\toptions\tflags[watchdog_status_flags, int32]",
        "\tfirmware_version\tint32",
        "\tidentity\tarray[int8, 32]",
        "}",
        "",
        "watchdog_status_flags = " + ", ".join(STATUS_FLAGS),
        "watchdog_set_options = " + ", ".join(SET_OPTIONS),
    ]
)

Path("dev_watchdog_ctl.txt").write_text("\n".join(txt_lines) + "\n")

const_lines = [
    "arches = amd64, 386",
    "",
]

for ioctl in ioctls:
    const_lines.append(
        f"{ioctl['name']} = {encode_ioctl(ioctl['encoding'], ioctl['nr'], SIZEOF[ioctl['arg_type']])}"
    )

const_lines.append("")
for name in STATUS_FLAGS + SET_OPTIONS:
    const_lines.append(f"{name} = {flags[name]}")

Path("dev_watchdog_ctl.txt.const").write_text("\n".join(const_lines) + "\n")
PY

cd /opt/syzkaller
make descriptions
