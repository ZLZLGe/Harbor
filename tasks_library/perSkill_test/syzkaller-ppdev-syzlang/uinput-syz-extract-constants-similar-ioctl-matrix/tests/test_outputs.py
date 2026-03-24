import os
import re
import subprocess

CONST_FILE = "/opt/syzkaller/sys/linux/dev_uinput.txt.const"
SYZLANG_FILE = "/opt/syzkaller/sys/linux/dev_uinput.txt"
SCAFFOLD_FILE = "/task-assets/dev_uinput.txt"

REQUIRED_CONSTS = {
    "UI_DEV_CREATE",
    "UI_DEV_DESTROY",
    "UI_DEV_SETUP",
    "UI_ABS_SETUP",
    "UI_GET_VERSION",
    "UI_SET_EVBIT",
    "UI_SET_KEYBIT",
    "UI_SET_RELBIT",
    "UI_SET_PROPBIT",
    "EV_KEY",
    "EV_REL",
    "KEY_SPACE",
    "BTN_LEFT",
    "REL_X",
    "REL_Y",
    "INPUT_PROP_POINTER",
}


def _ioc(direction, type_char, number, size):
    return (direction << 30) | (size << 16) | (ord(type_char) << 8) | number


EXPECTED_VALUES = {
    "UI_DEV_CREATE": _ioc(0, "U", 1, 0),
    "UI_DEV_DESTROY": _ioc(0, "U", 2, 0),
    "UI_DEV_SETUP": _ioc(1, "U", 3, 92),
    "UI_ABS_SETUP": _ioc(1, "U", 4, 28),
    "UI_GET_VERSION": _ioc(2, "U", 45, 4),
    "UI_SET_EVBIT": _ioc(1, "U", 100, 4),
    "UI_SET_KEYBIT": _ioc(1, "U", 101, 4),
    "UI_SET_RELBIT": _ioc(1, "U", 102, 4),
    "UI_SET_PROPBIT": _ioc(1, "U", 110, 4),
    "EV_KEY": 1,
    "EV_REL": 2,
    "KEY_SPACE": 57,
    "BTN_LEFT": 272,
    "REL_X": 0,
    "REL_Y": 1,
    "INPUT_PROP_POINTER": 0,
}


def read(path):
    assert os.path.exists(path), f"missing file: {path}"
    with open(path) as f:
        return f.read()


def parse_const_file():
    content = read(CONST_FILE)
    arches = None
    consts = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("arches"):
            _, rhs = line.split("=", 1)
            arches = {item.strip() for item in rhs.split(",") if item.strip()}
            continue
        if "=" not in line:
            continue
        name, rhs = line.split("=", 1)
        consts[name.strip()] = int(rhs.strip().split()[0], 0)
    return arches, consts


class TestScaffold:
    def test_scaffold_is_unchanged(self):
        assert read(SYZLANG_FILE) == read(SCAFFOLD_FILE), "dev_uinput.txt should remain the provided scaffold"

    def test_scaffold_references_expected_constant_groups(self):
        content = read(SYZLANG_FILE)
        for token in ["UI_SET_EVBIT", "UI_DEV_SETUP", "EV_KEY", "KEY_SPACE", "REL_X", "INPUT_PROP_POINTER"]:
            assert token in content, f"scaffold is missing expected token {token}"


class TestConstFile:
    def test_const_file_exists_and_targets_two_arches(self):
        arches, consts = parse_const_file()
        assert arches == {"amd64", "386"}, f"unexpected arches declaration: {arches}"
        assert REQUIRED_CONSTS.issubset(consts), f"missing constants: {sorted(REQUIRED_CONSTS - set(consts))}"

    def test_const_values_match_uapi_expectations(self):
        _, consts = parse_const_file()
        for name, expected in EXPECTED_VALUES.items():
            assert consts.get(name) == expected, f"{name} expected {expected}, got {consts.get(name)}"

    def test_placeholder_text_is_gone(self):
        content = read(CONST_FILE)
        assert "Fill the uinput constants" not in content
        assert "TODO" not in content


class TestBuild:
    def test_make_descriptions(self):
        result = subprocess.run(
            ["make", "descriptions"],
            cwd="/opt/syzkaller",
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"make descriptions failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    def test_sysgen_does_not_report_missing_uinput_constants(self):
        result = subprocess.run(
            ["make", "descriptions"],
            cwd="/opt/syzkaller",
            capture_output=True,
            text=True,
            timeout=300,
        )
        combined = result.stdout + result.stderr
        assert not re.search(r"defined for none of the arches", combined), combined
