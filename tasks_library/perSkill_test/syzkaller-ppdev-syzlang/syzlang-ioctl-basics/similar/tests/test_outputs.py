import re
import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_ppdiag.txt")


def read_clean() -> str:
    assert TARGET.exists(), f"missing output file: {TARGET}"
    lines = []
    for line in TARGET.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def test_make_targets_pass():
    result = subprocess.run(["make", "descriptions"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout
    result = subprocess.run(["make", "all"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout


def test_required_patterns():
    content = read_clean()
    assert re.search(r"resource\s+fd_ppdiag\s*\[\s*fd\s*\]", content)
    assert '"/dev/parport#"' in content
    assert re.search(r"ppdiag_window\s*\{[\s\S]*mask\s+int8[\s\S]*value\s+int8", content)
    assert re.search(r"ppdiag_modes\s*=\s*PPDIAG_MODE_COMPAT,\s*PPDIAG_MODE_ECP,\s*PPDIAG_MODE_EPP", content)
    assert re.search(r"ioctl\$PPDIAG_GETMODE\s*\([^)]*ptr\s*\[\s*out\s*,\s*int32\s*\]", content)
    assert re.search(r"ioctl\$PPDIAG_SETMODE\s*\([^)]*ptr\s*\[\s*in\s*,\s*flags\[ppdiag_modes,\s*int32\]\s*\]", content)


def test_ioctl_count_and_directions():
    content = read_clean()
    ioctls = re.findall(r"ioctl\$([A-Z0-9_]+)", content)
    assert len(ioctls) == 7, ioctls
    assert set(ioctls) == {
        "PPDIAG_CLAIM",
        "PPDIAG_RELEASE",
        "PPDIAG_GETMODE",
        "PPDIAG_SETMODE",
        "PPDIAG_READ_STATUS",
        "PPDIAG_WRITE_CTRL",
        "PPDIAG_FROB",
    }
    assert re.search(r"ioctl\$PPDIAG_READ_STATUS\s*\([^)]*ptr\s*\[\s*out\s*,\s*int8\s*\]", content)
    assert re.search(r"ioctl\$PPDIAG_WRITE_CTRL\s*\([^)]*ptr\s*\[\s*in\s*,\s*int8\s*\]", content)
    assert re.search(r"ioctl\$PPDIAG_FROB\s*\([^)]*ptr\s*\[\s*in\s*,\s*ppdiag_window\s*\]", content)
