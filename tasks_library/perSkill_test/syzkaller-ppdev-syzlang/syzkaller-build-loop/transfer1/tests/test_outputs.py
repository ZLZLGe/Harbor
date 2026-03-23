import subprocess
from pathlib import Path

TEXT = Path("/opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt")
CONST = Path("/opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt.const")


def test_make_targets_pass():
    result = subprocess.run(["make", "descriptions"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout
    result = subprocess.run(["make", "all"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout


def test_fixed_outputs_present():
    text = TEXT.read_text(encoding="utf-8")
    const = CONST.read_text(encoding="utf-8")
    assert "resource fd_sensorhub[fd]" in text
    assert "ptr[out, sensor_snapshot]" in text
    assert "ptr[in, sensor_threshold]" in text
    assert "arches = amd64, 386" in const
    assert "SENSOR_MODE_STREAM = 2" in const
