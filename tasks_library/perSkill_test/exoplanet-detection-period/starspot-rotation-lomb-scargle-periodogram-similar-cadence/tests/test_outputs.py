from pathlib import Path

EXPECTED_PERIOD = 8.73400
TOLERANCE = 0.15
OUTPUT_PATHS = [Path("/root/rotation_period.txt"), Path("rotation_period.txt")]


def read_output() -> str:
    for path in OUTPUT_PATHS:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    raise AssertionError("Missing /root/rotation_period.txt")


def test_output_exists():
    read_output()


def test_output_is_single_number():
    content = read_output()
    parts = content.split()
    assert len(parts) == 1, f"Expected one numeric value, got: {content!r}"
    value = float(parts[0])
    assert value > 0.0, f"Period must be positive, got {value}"


def test_output_matches_rotation_period():
    value = float(read_output())
    assert abs(value - EXPECTED_PERIOD) <= TOLERANCE, (
        f"Expected a rotation period near {EXPECTED_PERIOD:.5f} days, got {value:.5f}"
    )


def test_output_precision():
    content = read_output()
    assert "." in content, f"Expected a decimal representation, got {content!r}"
    decimals = len(content.split(".")[-1])
    assert decimals == 5, f"Expected exactly 5 decimal places, got {content!r}"
