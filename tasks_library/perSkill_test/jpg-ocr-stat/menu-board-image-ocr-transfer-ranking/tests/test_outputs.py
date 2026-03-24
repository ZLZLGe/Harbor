import json
import re
from pathlib import Path


OUTPUT_FILE = Path("/app/workspace/menu_price_report.md")
EXPECTED_FILE = Path("/tests/menu_report_oracle.json")
INPUT_DIR = Path("/app/workspace/menu_boards")
TABLE_ROW_RE = re.compile(r"^\| (?P<left>.+?) \| (?P<right>.+?) \|$")
CHEAPEST_RE = re.compile(r"^Cheapest item: (?P<item>.+?) \| (?P<price>\d+\.\d{2})$")
COUNT_RE = re.compile(r"^Total items: (?P<count>\d+)$")
MEDIAN_RE = re.compile(r"^Overall median price: (?P<price>\d+\.\d{2})$")


def load_expected() -> dict:
    return json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))


def parse_sections(text: str) -> list[tuple[str, list[str]]]:
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = None
    current_body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, current_body))
            current_title = line[3:].strip()
            current_body = []
        elif current_title is not None:
            current_body.append(line)
    if current_title is not None:
        sections.append((current_title, current_body))
    return sections


def parse_table(section_lines: list[str]) -> list[dict[str, str]]:
    table_lines = [line.strip() for line in section_lines if line.strip().startswith("|")]
    assert len(table_lines) >= 2, "Each board section must contain a Markdown table with a header and separator."
    assert table_lines[0] == "| item | price |", f"Unexpected table header: {table_lines[0]!r}"
    assert table_lines[1] == "| --- | --- |", f"Unexpected table separator: {table_lines[1]!r}"
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        match = TABLE_ROW_RE.match(line)
        assert match, f"Malformed table row: {line!r}"
        rows.append({"item": match.group("left"), "price": match.group("right")})
    return rows


def parse_summary(section_lines: list[str]) -> dict[str, str]:
    stripped = [line.strip() for line in section_lines if line.strip()]
    assert len(stripped) == 2, (
        "Summary section must contain exactly two non-empty lines: "
        "`Total items` and `Overall median price`."
    )
    count_match = COUNT_RE.match(stripped[0])
    assert count_match, f"Malformed summary count line: {stripped[0]!r}"
    median_match = MEDIAN_RE.match(stripped[1])
    assert median_match, f"Malformed median line: {stripped[1]!r}"
    return {
        "total_items": int(count_match.group("count")),
        "overall_median_price": median_match.group("price"),
    }


def test_output_report() -> None:
    assert OUTPUT_FILE.exists(), "menu_price_report.md not found at /app/workspace"
    assert EXPECTED_FILE.exists(), "menu_report_oracle.json is missing from /tests"
    assert INPUT_DIR.exists(), "menu_boards input directory is missing"

    expected = load_expected()
    report = OUTPUT_FILE.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert report.startswith("# Menu Price Report\n"), "Report must start with `# Menu Price Report`."

    sections = parse_sections(report)
    actual_titles = [title for title, _ in sections]
    expected_titles = expected["board_order"] + ["Summary"]
    assert actual_titles == expected_titles, (
        "Section order mismatch.\n"
        f"Actual: {actual_titles}\n"
        f"Expected: {expected_titles}"
    )

    input_files = sorted(path.name for path in INPUT_DIR.iterdir() if path.is_file())
    assert expected["board_order"] == input_files, (
        "Oracle board order must match input files exactly.\n"
        f"Oracle: {expected['board_order']}\n"
        f"Input: {input_files}"
    )

    for title, section_lines in sections[:-1]:
        expected_board = expected["boards"][title]
        actual_rows = parse_table(section_lines)
        assert actual_rows == expected_board["items"], (
            f"Item table mismatch for {title}.\n"
            f"Actual: {actual_rows}\n"
            f"Expected: {expected_board['items']}"
        )

        price_values = [row["price"] for row in actual_rows]
        assert price_values == sorted(price_values, key=lambda value: float(value)), (
            f"Rows for {title} must be ordered by price ascending.\n"
            f"Actual prices: {price_values}"
        )

        non_empty_lines = [line.strip() for line in section_lines if line.strip()]
        cheapest_line = non_empty_lines[-1]
        cheapest_match = CHEAPEST_RE.match(cheapest_line)
        assert cheapest_match, f"Malformed cheapest-item line for {title}: {cheapest_line!r}"
        assert cheapest_match.group("item") == expected_board["cheapest_item"], (
            f"Wrong cheapest item for {title}: {cheapest_match.group('item')!r}"
        )
        assert cheapest_match.group("price") == expected_board["cheapest_price"], (
            f"Wrong cheapest price for {title}: {cheapest_match.group('price')!r}"
        )

    summary = parse_summary(sections[-1][1])
    assert summary["total_items"] == expected["summary"]["total_items"], (
        "Total items mismatch.\n"
        f"Actual: {summary['total_items']}\n"
        f"Expected: {expected['summary']['total_items']}"
    )
    assert summary["overall_median_price"] == expected["summary"]["overall_median_price"], (
        "Median price mismatch.\n"
        f"Actual: {summary['overall_median_price']}\n"
        f"Expected: {expected['summary']['overall_median_price']}"
    )


if __name__ == "__main__":
    test_output_report()
