import re
import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt")


def content() -> str:
    assert TARGET.exists(), f"missing output file: {TARGET}"
    return TARGET.read_text(encoding="utf-8")


def test_make_targets_pass():
    result = subprocess.run(["make", "descriptions"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout
    result = subprocess.run(["make", "all"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout


def test_required_symbols():
    text = content()
    assert "resource fd_sensorhub[fd]" in text
    assert '"/dev/sensorhub#"' in text
    assert re.search(r"sensor_threshold\s*\{[\s\S]*channel\s+int16[\s\S]*limit\s+int32[\s\S]*hysteresis\s+int16", text)
    assert re.search(r"sensor_snapshot\s*\{[\s\S]*ambient\s+int32[\s\S]*surface\s+int32[\s\S]*humidity\s+int16", text)
    assert re.search(r"sensor_modes\s*=\s*SENSOR_MODE_IDLE,\s*SENSOR_MODE_FAST,\s*SENSOR_MODE_STREAM", text)


def test_ioctl_shapes():
    text = content()
    ioctls = re.findall(r"ioctl\$([A-Z0-9_]+)", text)
    assert set(ioctls) == {
        "SNS_ENABLE",
        "SNS_DISABLE",
        "SNS_GET_SNAPSHOT",
        "SNS_SET_THRESH",
        "SNS_SET_MODE",
    }
    assert re.search(r"ioctl\$SNS_GET_SNAPSHOT\s*\([^)]*ptr\s*\[\s*out\s*,\s*sensor_snapshot\s*\]", text)
    assert re.search(r"ioctl\$SNS_SET_THRESH\s*\([^)]*ptr\s*\[\s*in\s*,\s*sensor_threshold\s*\]", text)
    assert re.search(r"ioctl\$SNS_SET_MODE\s*\([^)]*ptr\s*\[\s*in\s*,\s*flags\[sensor_modes,\s*int32\]\s*\]", text)
