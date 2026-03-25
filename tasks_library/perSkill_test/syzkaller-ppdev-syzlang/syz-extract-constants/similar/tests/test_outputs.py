import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_ppdiag.txt.const")


def parse():
    assert TARGET.exists(), f"missing output file: {TARGET}"
    values = {}
    arch_line = None
    for raw_line in TARGET.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("arches"):
            arch_line = line
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = int(value.strip(), 0)
    return arch_line, values


def test_make_targets_pass():
    result = subprocess.run(["make", "descriptions"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout
    result = subprocess.run(["make", "all"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout


def test_expected_values():
    arch_line, values = parse()
    assert arch_line == "arches = amd64, 386"
    assert values["PPDIAG_CLAIM"] == 28736
    assert values["PPDIAG_RELEASE"] == 28737
    assert values["PPDIAG_GETMODE"] == 2147774530
    assert values["PPDIAG_SETMODE"] == 1074032707
    assert values["PPDIAG_READ_STATUS"] == 2147577924
    assert values["PPDIAG_WRITE_CTRL"] == 1073836101
    assert values["PPDIAG_FROB"] == 1073901638
    assert values["PPDIAG_MODE_COMPAT"] == 1
    assert values["PPDIAG_MODE_ECP"] == 16
    assert values["PPDIAG_MODE_EPP"] == 256
