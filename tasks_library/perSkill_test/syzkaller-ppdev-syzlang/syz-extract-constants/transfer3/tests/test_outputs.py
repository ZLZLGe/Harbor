import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_bridge_port.txt.const")


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
    assert values["BPORT_SET_PORT"] == 1073898064
    assert values["BPORT_QUERY_PORT"] == 3221381713
    assert values["BPORT_GET_INDEX"] == 2147770962
    assert values["BPORT_CLEAR_STATS"] == 25171
    assert values["BR_PORT_UP"] == 1
    assert values["BR_PORT_LEARNING"] == 4
    assert values["BR_PORT_FLOOD"] == 16
