import os
import re
import subprocess
import tempfile
from pathlib import Path


SYZLANG_FILE = Path("/opt/syzkaller/sys/linux/dev_watchdog_ctl.txt")
CONST_FILE = Path("/opt/syzkaller/sys/linux/dev_watchdog_ctl.txt.const")

EXPECTED_SIGNATURES = {
    "WDIOC_GETSUPPORT": "ioctl$WDIOC_GETSUPPORT(fdfd_watchdog,cmdconst[WDIOC_GETSUPPORT],argptr[out,watchdog_info])",
    "WDIOC_GETSTATUS": "ioctl$WDIOC_GETSTATUS(fdfd_watchdog,cmdconst[WDIOC_GETSTATUS],argptr[out,int32])",
    "WDIOC_GETBOOTSTATUS": "ioctl$WDIOC_GETBOOTSTATUS(fdfd_watchdog,cmdconst[WDIOC_GETBOOTSTATUS],argptr[out,int32])",
    "WDIOC_GETTEMP": "ioctl$WDIOC_GETTEMP(fdfd_watchdog,cmdconst[WDIOC_GETTEMP],argptr[out,int32])",
    "WDIOC_SETOPTIONS": "ioctl$WDIOC_SETOPTIONS(fdfd_watchdog,cmdconst[WDIOC_SETOPTIONS],argptr[in,flags[watchdog_set_options,int32]])",
    "WDIOC_KEEPALIVE": "ioctl$WDIOC_KEEPALIVE(fdfd_watchdog,cmdconst[WDIOC_KEEPALIVE])",
    "WDIOC_SETTIMEOUT": "ioctl$WDIOC_SETTIMEOUT(fdfd_watchdog,cmdconst[WDIOC_SETTIMEOUT],argptr[inout,int32])",
    "WDIOC_GETTIMEOUT": "ioctl$WDIOC_GETTIMEOUT(fdfd_watchdog,cmdconst[WDIOC_GETTIMEOUT],argptr[out,int32])",
    "WDIOC_SETPRETIMEOUT": "ioctl$WDIOC_SETPRETIMEOUT(fdfd_watchdog,cmdconst[WDIOC_SETPRETIMEOUT],argptr[inout,int32])",
    "WDIOC_GETPRETIMEOUT": "ioctl$WDIOC_GETPRETIMEOUT(fdfd_watchdog,cmdconst[WDIOC_GETPRETIMEOUT],argptr[out,int32])",
    "WDIOC_GETTIMELEFT": "ioctl$WDIOC_GETTIMELEFT(fdfd_watchdog,cmdconst[WDIOC_GETTIMELEFT],argptr[out,int32])",
}

STATUS_FLAGS = [
    "WDIOF_OVERHEAT",
    "WDIOF_FANFAULT",
    "WDIOF_EXTERN1",
    "WDIOF_EXTERN2",
    "WDIOF_POWERUNDER",
    "WDIOF_CARDRESET",
    "WDIOF_POWEROVER",
    "WDIOF_SETTIMEOUT",
    "WDIOF_MAGICCLOSE",
    "WDIOF_PRETIMEOUT",
    "WDIOF_ALARMONLY",
    "WDIOF_KEEPALIVEPING",
]

SET_OPTION_FLAGS = [
    "WDIOS_DISABLECARD",
    "WDIOS_ENABLECARD",
    "WDIOS_TEMPPANIC",
]


def read(path: Path) -> str:
    assert path.exists(), f"{path} does not exist"
    return path.read_text()


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def parse_const_file():
    consts = {}
    for raw_line in read(CONST_FILE).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("arches"):
            continue
        name, value = [part.strip() for part in line.split("=", 1)]
        consts[name] = int(value, 0)
    return consts


def parse_flag_set(text: str, set_name: str):
    match = re.search(rf"{set_name}\s*=\s*(.+)", text)
    assert match, f"{set_name} is not defined"
    return {item.strip() for item in match.group(1).split(",") if item.strip()}


def live_watchdog_constants():
    code = r"""
    #include <linux/watchdog.h>
    #include <stdio.h>

    int main(void) {
        printf("WDIOC_GETSUPPORT=%llu\n", (unsigned long long)WDIOC_GETSUPPORT);
        printf("WDIOC_GETSTATUS=%llu\n", (unsigned long long)WDIOC_GETSTATUS);
        printf("WDIOC_GETBOOTSTATUS=%llu\n", (unsigned long long)WDIOC_GETBOOTSTATUS);
        printf("WDIOC_GETTEMP=%llu\n", (unsigned long long)WDIOC_GETTEMP);
        printf("WDIOC_SETOPTIONS=%llu\n", (unsigned long long)WDIOC_SETOPTIONS);
        printf("WDIOC_KEEPALIVE=%llu\n", (unsigned long long)WDIOC_KEEPALIVE);
        printf("WDIOC_SETTIMEOUT=%llu\n", (unsigned long long)WDIOC_SETTIMEOUT);
        printf("WDIOC_GETTIMEOUT=%llu\n", (unsigned long long)WDIOC_GETTIMEOUT);
        printf("WDIOC_SETPRETIMEOUT=%llu\n", (unsigned long long)WDIOC_SETPRETIMEOUT);
        printf("WDIOC_GETPRETIMEOUT=%llu\n", (unsigned long long)WDIOC_GETPRETIMEOUT);
        printf("WDIOC_GETTIMELEFT=%llu\n", (unsigned long long)WDIOC_GETTIMELEFT);
        printf("WDIOF_OVERHEAT=%u\n", WDIOF_OVERHEAT);
        printf("WDIOF_FANFAULT=%u\n", WDIOF_FANFAULT);
        printf("WDIOF_EXTERN1=%u\n", WDIOF_EXTERN1);
        printf("WDIOF_EXTERN2=%u\n", WDIOF_EXTERN2);
        printf("WDIOF_POWERUNDER=%u\n", WDIOF_POWERUNDER);
        printf("WDIOF_CARDRESET=%u\n", WDIOF_CARDRESET);
        printf("WDIOF_POWEROVER=%u\n", WDIOF_POWEROVER);
        printf("WDIOF_SETTIMEOUT=%u\n", WDIOF_SETTIMEOUT);
        printf("WDIOF_MAGICCLOSE=%u\n", WDIOF_MAGICCLOSE);
        printf("WDIOF_PRETIMEOUT=%u\n", WDIOF_PRETIMEOUT);
        printf("WDIOF_ALARMONLY=%u\n", WDIOF_ALARMONLY);
        printf("WDIOF_KEEPALIVEPING=%u\n", WDIOF_KEEPALIVEPING);
        printf("WDIOS_DISABLECARD=%u\n", WDIOS_DISABLECARD);
        printf("WDIOS_ENABLECARD=%u\n", WDIOS_ENABLECARD);
        printf("WDIOS_TEMPPANIC=%u\n", WDIOS_TEMPPANIC);
        return 0;
    }
    """
    with tempfile.TemporaryDirectory() as td:
        c_path = Path(td) / "watchdog_consts.c"
        bin_path = Path(td) / "watchdog_consts"
        c_path.write_text(code)
        compile_result = subprocess.run(
            ["gcc", str(c_path), "-o", str(bin_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert compile_result.returncode == 0, compile_result.stderr
        run_result = subprocess.run(
            [str(bin_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert run_result.returncode == 0, run_result.stderr
    pairs = {}
    for line in run_result.stdout.splitlines():
        name, value = line.strip().split("=", 1)
        pairs[name] = int(value, 0)
    return pairs


def test_files_exist():
    assert SYZLANG_FILE.exists()
    assert CONST_FILE.exists()


def test_make_descriptions_succeeds():
    result = subprocess.run(
        ["make", "descriptions"],
        cwd="/opt/syzkaller",
        capture_output=True,
        text=True,
        timeout=300,
        env=os.environ.copy(),
    )
    assert result.returncode == 0, f"make descriptions failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def test_resource_open_struct_and_flag_sets():
    content = read(SYZLANG_FILE)
    compact = normalize(content)

    assert "include<linux/watchdog.h>" in compact
    assert "resourcefd_watchdog[fd]" in compact
    assert re.search(r'syz_open_dev(?:\$\w+)?\(.*"/dev/watchdog#".*\)\s+fd_watchdog', content, re.DOTALL)

    assert "watchdog_info{" in compact
    assert "optionsflags[watchdog_status_flags,int32]" in compact
    assert "firmware_versionint32" in compact
    assert "identityarray[int8,32]" in compact

    assert parse_flag_set(content, "watchdog_status_flags") == set(STATUS_FLAGS)
    assert parse_flag_set(content, "watchdog_set_options") == set(SET_OPTION_FLAGS)


def test_ioctl_signatures_match_required_contract():
    compact = normalize(read(SYZLANG_FILE))
    missing = [name for name, signature in EXPECTED_SIGNATURES.items() if signature not in compact]
    assert not missing, f"Missing or incorrect ioctl signatures: {missing}"


def test_const_file_matches_live_header_values():
    const_content = read(CONST_FILE)
    assert re.search(r"^\s*arches\s*=\s*amd64\s*,\s*386\s*$", const_content, re.MULTILINE)

    parsed = parse_const_file()
    live = live_watchdog_constants()

    for name in list(EXPECTED_SIGNATURES) + STATUS_FLAGS + SET_OPTION_FLAGS:
        assert name in parsed, f"{name} missing from const file"
        assert parsed[name] == live[name], f"{name} has value {parsed[name]}, expected {live[name]}"
