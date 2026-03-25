import json
import re
import subprocess
import tempfile
from pathlib import Path

CONST_FILE = Path("/opt/syzkaller/sys/linux/dev_demo_compat.txt.const")
MANIFEST_FILE = Path("/opt/task-assets/compat_manifest.json")
HEADER_ROOT = Path("/opt/task-assets/mock-uapi")
VERIFY_SCRIPT = Path("/opt/task-assets/verify_demo_compat.py")
ARCH_FLAGS = {
    "amd64": "-m64",
    "386": "-m32",
}


def load_manifest():
    return json.loads(MANIFEST_FILE.read_text())


def parse_const_file():
    values = {}
    content = CONST_FILE.read_text()
    for raw in content.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("arches"):
            continue
        if "=" not in line:
            continue
        name, rhs = [part.strip() for part in line.split("=", 1)]
        if ":" not in rhs:
            values[name] = int(rhs, 0)
            continue
        per_arch = {}
        for chunk in rhs.split(","):
            arch, value = [part.strip() for part in chunk.split(":", 1)]
            per_arch[arch] = int(value, 0)
        values[name] = per_arch
    return values


def resolve_value(values, name, arch):
    value = values[name]
    if isinstance(value, dict):
        return value[arch]
    return value


def compile_expected(arch, symbols):
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "expected_consts.c"
        binary = Path(tmpdir) / "expected_consts"
        lines = [
            "#include <stdio.h>",
            "#include <linux/dev_demo_compat.h>",
            "int main(void) {",
        ]
        for symbol in symbols:
            lines.append(f'    printf("{symbol}=%llu\\n", (unsigned long long){symbol});')
        lines.extend(
            [
                "    return 0;",
                "}",
            ]
        )
        src.write_text("\n".join(lines) + "\n")
        result = subprocess.run(
            ["gcc", ARCH_FLAGS[arch], "-I", str(HEADER_ROOT), str(src), "-o", str(binary)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
        output = subprocess.check_output([str(binary)], text=True)
    expected = {}
    for line in output.splitlines():
        name, value = line.split("=", 1)
        expected[name] = int(value, 0)
    return expected


def test_arches_line_and_required_symbols_exist():
    assert CONST_FILE.exists(), f"missing {CONST_FILE}"
    content = CONST_FILE.read_text()
    assert re.search(r"^arches\s*=\s*amd64,\s*386\s*$", content, re.M)

    manifest = load_manifest()
    values = parse_const_file()
    for item in manifest["symbols"]:
        assert item["name"] in values, f"missing {item['name']}"


def test_size_sensitive_ioctls_are_split_by_arch():
    manifest = load_manifest()
    values = parse_const_file()

    for item in manifest["symbols"]:
        if not item.get("arch_sensitive"):
            continue
        value = values[item["name"]]
        assert isinstance(value, dict), f"{item['name']} must use amd64:<value>, 386:<value>"
        assert set(value) == {"amd64", "386"}, f"{item['name']} must provide amd64 and 386 values"
        assert value["amd64"] != value["386"], f"{item['name']} should differ across amd64 and 386"


def test_numeric_values_match_header_for_both_arches():
    manifest = load_manifest()
    symbols = [item["name"] for item in manifest["symbols"]]
    values = parse_const_file()

    for arch in ("amd64", "386"):
        expected = compile_expected(arch, symbols)
        for symbol in symbols:
            assert resolve_value(values, symbol, arch) == expected[symbol], (
                f"{arch}: {symbol} mismatch"
            )


def test_documented_verifier_passes_for_amd64_and_386():
    for arch in ("amd64", "386"):
        result = subprocess.run(
            ["python3", str(VERIFY_SCRIPT), arch],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
