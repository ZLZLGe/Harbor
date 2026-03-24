import re
from pathlib import Path


OUTPUT_FILE = Path("/app/workspace/site_safety_delta.md")
EXPECTED_ROWS = [
    ("bay_alpha", 1, 2, 1, 1, "elevated"),
    ("mixing_yard", 2, 1, 1, 2, "critical"),
    ("pump_station", 0, 3, 0, 1, "elevated"),
    ("service_tunnel", 3, 0, 2, 0, "critical"),
    ("west_ramp", 0, 1, 0, 0, "watch"),
]
EXPECTED_TOTALS = {
    "missing_guardrails": 6,
    "removed_warning_cones": 7,
    "uncovered_holes": 4,
    "workers_without_helmets": 4,
}
EXPECTED_CRITICAL = "mixing_yard, service_tunnel"
AREA_HEADER = "| area_id | missing_guardrails | removed_warning_cones | uncovered_holes | workers_without_helmets | risk_level |"
TOTAL_HEADER = "| metric | count |"


def extract_section(lines: list[str], header: str) -> list[str]:
    start = lines.index(header)
    rows: list[str] = []
    for line in lines[start + 2:]:
        if not line.strip():
            break
        rows.append(line)
    return rows


def parse_pipe_row(line: str) -> list[str]:
    assert line.startswith("|") and line.endswith("|"), f"Invalid markdown table row: {line}"
    return [part.strip() for part in line.strip("|").split("|")]


def expected_level(guardrails: int, cones: int, holes: int, helmets: int) -> str:
    total = guardrails + cones + holes + helmets
    if holes >= 2 or helmets >= 2 or total >= 6:
        return "critical"
    if total >= 3:
        return "elevated"
    if total >= 1:
        return "watch"
    return "stable"


def test_markdown_report() -> None:
    assert OUTPUT_FILE.exists(), "Missing /app/workspace/site_safety_delta.md"
    text = OUTPUT_FILE.read_text(encoding="utf-8")

    assert text.startswith("# 施工现场安全变化报告\n"), "Report must start with the required title"
    assert "只统计从 before 到 after 新增或恶化的风险。" in text, "Missing required scope sentence"
    assert "\n## 区域变化表\n" in text, "Missing 区域变化表 section"
    assert "\n## 总计\n" in text, "Missing 总计 section"

    lines = text.splitlines()
    assert AREA_HEADER in lines, "Missing or malformed area summary table header"
    assert TOTAL_HEADER in lines, "Missing or malformed total table header"

    area_lines = extract_section(lines, AREA_HEADER)
    assert len(area_lines) == len(EXPECTED_ROWS), f"Expected {len(EXPECTED_ROWS)} area rows, got {len(area_lines)}"

    parsed_rows = []
    for line in area_lines:
        cols = parse_pipe_row(line)
        assert len(cols) == 6, f"Unexpected area table column count: {cols}"
        area_id = cols[0]
        numbers = [int(value) for value in cols[1:5]]
        risk_level = cols[5]
        assert risk_level in {"stable", "watch", "elevated", "critical"}, f"Unexpected risk level: {risk_level}"
        parsed_rows.append((area_id, *numbers, risk_level))

    assert parsed_rows == EXPECTED_ROWS, f"Area table mismatch.\nActual: {parsed_rows}\nExpected: {EXPECTED_ROWS}"

    area_ids = [row[0] for row in parsed_rows]
    assert area_ids == sorted(area_ids), "area_id rows must be sorted ascending"

    for area_id, guardrails, cones, holes, helmets, risk_level in parsed_rows:
        assert risk_level == expected_level(guardrails, cones, holes, helmets), (
            f"Risk level rule mismatch for {area_id}: got {risk_level}"
        )

    total_lines = extract_section(lines, TOTAL_HEADER)
    assert len(total_lines) == len(EXPECTED_TOTALS), f"Expected {len(EXPECTED_TOTALS)} total rows, got {len(total_lines)}"

    parsed_totals = {}
    for line in total_lines:
        cols = parse_pipe_row(line)
        assert len(cols) == 2, f"Unexpected total table column count: {cols}"
        parsed_totals[cols[0]] = int(cols[1])

    assert parsed_totals == EXPECTED_TOTALS, f"Total table mismatch.\nActual: {parsed_totals}\nExpected: {EXPECTED_TOTALS}"

    critical_match = re.search(r"^高风险区域: (.+)$", text, flags=re.MULTILINE)
    assert critical_match, "Missing 高风险区域 line"
    assert critical_match.group(1).strip() == EXPECTED_CRITICAL, (
        f"Unexpected high-risk area list: {critical_match.group(1).strip()}"
    )
