import subprocess
from pathlib import Path

TEXT = Path("/opt/syzkaller/sys/linux/dev_capring.txt")
CONST = Path("/opt/syzkaller/sys/linux/dev_capring.txt.const")


def test_make_targets_pass():
    result = subprocess.run(["make", "descriptions"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout
    result = subprocess.run(["make", "all"], cwd="/opt/syzkaller", capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr or result.stdout


def test_fixed_outputs_present():
    text = TEXT.read_text(encoding="utf-8")
    const = CONST.read_text(encoding="utf-8")
    assert "resource fd_capring[fd]" in text
    assert "ptr[out, array[int8, 64]]" in text
    assert "ptr[in, array[int8, 64]]" in text
    assert "CAPRING_GET_SLOT = 2147771185" in const
    assert "CAPRING_ENABLE_TRACE = 25395" in const
