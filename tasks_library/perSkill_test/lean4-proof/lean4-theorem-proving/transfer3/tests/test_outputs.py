import filecmp
import os
import pathlib

TARGET = "/app/workspace/transfer3.lean"
BASELINE = "/app/baseline/transfer3.lean"
EXPECTED = "/app/workspace/expected_transfer3.lean"
PREFIX_LINES = 5


def _read_lines(path: str) -> list[str]:
    return open(path, encoding="utf-8").read().splitlines()


def test_solution_exists() -> None:
    assert os.path.exists(TARGET), f"missing {TARGET}"


def test_prefix_exact() -> None:
    ws_lines = _read_lines(TARGET)
    base_lines = _read_lines(BASELINE)
    assert len(ws_lines) >= PREFIX_LINES
    assert len(base_lines) >= PREFIX_LINES
    for i, (got, exp) in enumerate(zip(ws_lines[:PREFIX_LINES], base_lines[:PREFIX_LINES]), start=1):
        assert got.rstrip() == exp.rstrip(), f"prefix mismatch at line {i}: got={got!r}, expected={exp!r}"


def test_expected_solution_exact() -> None:
    got = open(TARGET, encoding="utf-8").read().strip()
    exp = open(EXPECTED, encoding="utf-8").read().strip()
    assert got == exp, "solution content mismatch against expected proof"


def test_no_changes_outside_target() -> None:
    base = pathlib.Path("/app/baseline")
    work = pathlib.Path("/app/workspace")
    for p in base.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(base)
        if str(rel) == "transfer3.lean":
            continue
        q = work / rel
        assert q.exists(), f"missing file in workspace: {rel}"
        assert filecmp.cmp(p, q, shallow=False), f"modified non-target file: {rel}"
