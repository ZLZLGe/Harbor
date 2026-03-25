from pathlib import Path

OUT = Path("/root/transfer2_stage_windows.md")

EXPECTED = [
    ("cleanup", "Remove unnecessary geometry", 0.0, 42.0),
    ("faces", "Make the floor's faces", 42.0, 53.0),
    ("background", "Make the background", 53.0, 99.0),
    ("extrude_z", "Extruding the walls in Z", 99.0, 115.0),
    ("orientation_review", "Reviewing face orientation", 115.0, 154.0),
    ("wall_thickness_modifiers", "Adding thickness to walls with Modifiers", 154.0, 193.0),
]


def parse_row(line: str) -> tuple[str, str, float, float]:
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    assert len(parts) == 4, f"expected 4 columns, got {len(parts)} in line: {line}"
    return parts[0], parts[1], float(parts[2]), float(parts[3])


def main() -> None:
    assert OUT.exists(), f"missing output file: {OUT}"
    lines = [line.rstrip() for line in OUT.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert lines[0] == "# Stage Windows", "first line must be '# Stage Windows'"

    table_lines = [line for line in lines if line.startswith("|")]
    assert len(table_lines) == 8, f"expected 8 markdown table lines, got {len(table_lines)}"
    assert table_lines[0] == "| stage_key | label | start_seconds | end_seconds |"

    previous_start = -1.0
    for line, expected in zip(table_lines[2:], EXPECTED):
        stage_key, label, start, end = parse_row(line)
        exp_key, exp_label, exp_start, exp_end = expected

        assert stage_key == exp_key, f"stage key mismatch for {exp_key}"
        assert label == exp_label, f"label mismatch for {exp_key}"
        assert start > previous_start, f"start_seconds must be strictly increasing; got {start} after {previous_start}"
        assert end > start, f"end_seconds must be greater than start_seconds for {exp_key}"
        assert end <= 193.0, f"end_seconds exceeds clip duration for {exp_key}: {end}"
        assert abs(start - exp_start) <= 5.0, f"start_seconds too far off for {exp_key}"
        assert abs(end - exp_end) <= 5.0, f"end_seconds too far off for {exp_key}"

        previous_start = start


if __name__ == "__main__":
    main()
