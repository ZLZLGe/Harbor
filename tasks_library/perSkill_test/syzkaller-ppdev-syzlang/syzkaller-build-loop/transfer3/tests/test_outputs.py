import subprocess
from pathlib import Path

TEXT = Path("/opt/syzkaller/sys/linux/dev_bridge_port.txt")
CONST = Path("/opt/syzkaller/sys/linux/dev_bridge_port.txt.const")


def test_make_targets_pass():
    result = subprocess.run(["make", "descriptions"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout
    result = subprocess.run(["make", "all"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout


def test_fixed_outputs_present():
    text = TEXT.read_text(encoding="utf-8")
    const = CONST.read_text(encoding="utf-8")
    assert "resource fd_bridgectl[fd]" in text
    assert "ptr[inout, ifreq_t[int16]]" in text
    assert "ptr[out, int32]" in text
    assert "arches = amd64, 386" in const
    assert "BR_PORT_FLOOD = 16" in const
