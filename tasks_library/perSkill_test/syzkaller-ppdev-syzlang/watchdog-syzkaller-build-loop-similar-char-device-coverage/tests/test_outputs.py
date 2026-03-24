import os
import re
import subprocess

SYZLANG_FILE = "/opt/syzkaller/sys/linux/dev_watchdog.txt"
CONST_FILE = "/opt/syzkaller/sys/linux/dev_watchdog.txt.const"


def read_file(path):
    assert os.path.exists(path), f"missing file: {path}"
    with open(path) as f:
        return f.read()


def parse_const_file():
    consts = {}
    for line in read_file(CONST_FILE).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("arches"):
            continue
        name, value = [part.strip() for part in line.split("=", 1)]
        consts[name] = int(value.split(",", 1)[0].strip(), 0)
    return consts


class TestFiles:
    def test_required_files_and_include(self):
        content = read_file(SYZLANG_FILE)
        assert "include <linux/watchdog.h>" in content
        assert os.path.exists(CONST_FILE)

    def test_const_file_declares_arches(self):
        content = read_file(CONST_FILE)
        assert re.search(r"^\s*arches\s*=\s*amd64,\s*386\s*$", content, re.MULTILINE)


class TestCompilation:
    def test_make_descriptions(self):
        result = subprocess.run(
            ["make", "descriptions"],
            cwd="/opt/syzkaller",
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"make descriptions failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    def test_make_all_linux_amd64(self):
        result = subprocess.run(
            ["make", "all", "TARGETOS=linux", "TARGETARCH=amd64"],
            cwd="/opt/syzkaller",
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, f"make all failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


class TestDescriptions:
    def test_resource_and_opener(self):
        content = read_file(SYZLANG_FILE)
        assert re.search(r"resource\s+fd_watchdog\s*\[\s*fd\s*\]", content)
        assert re.search(r'syz_open_dev\$watchdog\([^)]*"/dev/watchdog#"', content)
        assert re.search(r"syz_open_dev\$watchdog[^)]*\)\s+fd_watchdog", content)

    def test_watchdog_info_layout(self):
        content = read_file(SYZLANG_FILE)
        match = re.search(r"watchdog_info\s*\{([^}]+)\}", content, re.DOTALL)
        assert match, "missing watchdog_info struct"
        body = match.group(1)
        assert re.search(r"options\s+flags\[watchdog_option_flags,\s*int32\]", body)
        assert re.search(r"firmware_version\s+int32", body)
        assert re.search(r"identity\s+array\[int8,\s*32\]", body)

    def test_required_ioctl_signatures(self):
        content = read_file(SYZLANG_FILE)
        expected_patterns = [
            r"ioctl\$WDIOC_GETSUPPORT\([^)]*ptr\[out,\s*watchdog_info\]",
            r"ioctl\$WDIOC_GETSTATUS\([^)]*ptr\[out,\s*flags\[watchdog_option_flags,\s*int32\]\]",
            r"ioctl\$WDIOC_GETBOOTSTATUS\([^)]*ptr\[out,\s*flags\[watchdog_option_flags,\s*int32\]\]",
            r"ioctl\$WDIOC_SETOPTIONS\([^)]*ptr\[in,\s*flags\[watchdog_setoptions,\s*int32\]\]",
            r"ioctl\$WDIOC_SETTIMEOUT\([^)]*ptr\[inout,\s*int32\]",
            r"ioctl\$WDIOC_GETTIMEOUT\([^)]*ptr\[out,\s*int32\]",
            r"ioctl\$WDIOC_SETPRETIMEOUT\([^)]*ptr\[inout,\s*int32\]",
            r"ioctl\$WDIOC_GETPRETIMEOUT\([^)]*ptr\[out,\s*int32\]",
            r"ioctl\$WDIOC_GETTIMELEFT\([^)]*ptr\[out,\s*int32\]",
        ]
        for pattern in expected_patterns:
            assert re.search(pattern, content), f"missing ioctl signature matching: {pattern}"

    def test_flag_sets_present(self):
        content = read_file(SYZLANG_FILE)
        assert re.search(r"watchdog_option_flags\s*=", content)
        assert "WDIOF_KEEPALIVEPING" in content
        assert "WDIOF_PRETIMEOUT" in content
        assert re.search(r"watchdog_setoptions\s*=", content)
        assert "WDIOS_DISABLECARD" in content
        assert "WDIOS_TEMPPANIC" in content


class TestConstants:
    def test_ioctl_constant_values(self):
        consts = parse_const_file()
        assert consts["WDIOC_GETSUPPORT"] == 2150127360
        assert consts["WDIOC_GETSTATUS"] == 2147768065
        assert consts["WDIOC_SETOPTIONS"] == 2147768068
        assert consts["WDIOC_SETTIMEOUT"] == 3221509894
        assert consts["WDIOC_SETPRETIMEOUT"] == 3221509896
        assert consts["WDIOC_GETTIMELEFT"] == 2147768074

    def test_flag_constant_values(self):
        consts = parse_const_file()
        assert consts["WDIOF_OVERHEAT"] == 1
        assert consts["WDIOF_POWEROVER"] == 64
        assert consts["WDIOF_ALARMONLY"] == 1024
        assert consts["WDIOF_KEEPALIVEPING"] == 32768
        assert consts["WDIOS_DISABLECARD"] == 1
        assert consts["WDIOS_ENABLECARD"] == 2
        assert consts["WDIOS_TEMPPANIC"] == 4
