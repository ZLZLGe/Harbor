import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_capring.txt.const")


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
    assert values["CAPRING_SET_SLOT"] == 1074029360
    assert values["CAPRING_GET_SLOT"] == 2147771185
    assert values["CAPRING_SUBMIT"] == 1074291506
    assert values["CAPRING_ENABLE_TRACE"] == 25395
    assert values["CAPRING_TRACE_BURST"] == 1
    assert values["CAPRING_TRACE_LOSSY"] == 2
