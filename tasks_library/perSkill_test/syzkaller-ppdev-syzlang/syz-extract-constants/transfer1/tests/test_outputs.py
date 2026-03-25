import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt.const")


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
    assert values["SNS_ENABLE"] == 29456
    assert values["SNS_DISABLE"] == 29457
    assert values["SNS_GET_SNAPSHOT"] == 2148168466
    assert values["SNS_SET_THRESH"] == 1074295571
    assert values["SNS_SET_MODE"] == 1074033428
    assert values["SENSOR_MODE_IDLE"] == 0
    assert values["SENSOR_MODE_FAST"] == 1
    assert values["SENSOR_MODE_STREAM"] == 2
