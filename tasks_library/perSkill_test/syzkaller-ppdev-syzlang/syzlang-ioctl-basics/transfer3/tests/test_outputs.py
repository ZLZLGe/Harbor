import re
import subprocess
from pathlib import Path

TARGET = Path("/opt/syzkaller/sys/linux/dev_bridge_port.txt")


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
    assert "include <linux/if.h>" in text
    assert "include <linux/sockios.h>" in text
    assert "resource fd_bridgectl[fd]" in text
    assert '"/dev/bridgectl#"' in text
    assert re.search(r"bridge_flags\s*=\s*BR_PORT_UP,\s*BR_PORT_LEARNING,\s*BR_PORT_FLOOD", text)


def test_ioctl_shapes():
    text = content()
    ioctls = re.findall(r"ioctl\$([A-Z0-9_]+)", text)
    assert set(ioctls) == {"BPORT_SET_PORT", "BPORT_QUERY_PORT", "BPORT_GET_INDEX"}
    assert re.search(r"ioctl\$BPORT_SET_PORT\s*\([^)]*ptr\s*\[\s*in\s*,\s*ifreq_t\[flags\[bridge_flags,\s*int16\]\]\s*\]", text)
    assert re.search(r"ioctl\$BPORT_QUERY_PORT\s*\([^)]*ptr\s*\[\s*inout\s*,\s*ifreq_t\[int16\]\s*\]", text)
    assert re.search(r"ioctl\$BPORT_GET_INDEX\s*\([^)]*ptr\s*\[\s*out\s*,\s*int32\s*\]", text)
