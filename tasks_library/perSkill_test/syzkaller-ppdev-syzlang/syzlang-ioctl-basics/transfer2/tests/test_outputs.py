import re
import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_capring.txt")


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
    assert "resource fd_capring[fd]" in text
    assert '"/dev/capring#"' in text
    assert re.search(r"capring_frame\s*\{[\s\S]*frame_id\s+int32[\s\S]*slot\s+int16[\s\S]*priority\s+int16", text)
    assert re.search(r"read\$capring\s*\([^)]*ptr\s*\[\s*out\s*,\s*array\[int8,\s*64\]\s*\][^)]*len\[buf\]", text)
    assert re.search(r"write\$capring\s*\([^)]*ptr\s*\[\s*in\s*,\s*array\[int8,\s*64\]\s*\][^)]*len\[buf\]", text)


def test_ioctl_shapes():
    text = content()
    ioctls = re.findall(r"ioctl\$([A-Z0-9_]+)", text)
    assert set(ioctls) == {"CAPRING_SET_SLOT", "CAPRING_GET_SLOT", "CAPRING_SUBMIT"}
    assert re.search(r"ioctl\$CAPRING_SET_SLOT\s*\([^)]*ptr\s*\[\s*in\s*,\s*int32\s*\]", text)
    assert re.search(r"ioctl\$CAPRING_GET_SLOT\s*\([^)]*ptr\s*\[\s*out\s*,\s*int32\s*\]", text)
    assert re.search(r"ioctl\$CAPRING_SUBMIT\s*\([^)]*ptr\s*\[\s*in\s*,\s*capring_frame\s*\]", text)
