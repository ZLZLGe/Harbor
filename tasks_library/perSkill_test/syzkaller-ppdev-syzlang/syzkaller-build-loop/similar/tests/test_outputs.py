import subprocess
from pathlib import Path

TEXT = Path("/opt/syzkaller/sys/linux/dev_ppdiag.txt")
CONST = Path("/opt/syzkaller/sys/linux/dev_ppdiag.txt.const")


def test_make_targets_pass():
    result = subprocess.run(["make", "descriptions"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout
    result = subprocess.run(["make", "all"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout


def test_fixed_outputs_present():
    text = TEXT.read_text(encoding="utf-8")
    const = CONST.read_text(encoding="utf-8")
    assert "resource fd_ppdiag[fd]" in text
    assert "ptr[out, int32]" in text
    assert "ptr[in, flags[ppdiag_modes, int32]]" in text
    assert "arches = amd64, 386" in const
    assert "PPDIAG_RELEASE = 28737" in const
