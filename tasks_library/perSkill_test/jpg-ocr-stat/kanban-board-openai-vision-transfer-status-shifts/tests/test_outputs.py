import json
from pathlib import Path


OUTPUT_FILE = Path("/app/workspace/kanban_status_diff.ndjson")
ALLOWED_COLUMNS = {"Queued", "Building", "Review", "Shipped"}
EXPECTED_RECORDS = [
    {"card_text": "ALERT COPY", "from_column": "Queued", "to_column": "Queued", "change_type": "unchanged"},
    {"card_text": "API DOCS", "from_column": "Queued", "to_column": "Building", "change_type": "moved"},
    {"card_text": "BETA NOTES", "from_column": "Shipped", "to_column": "Shipped", "change_type": "unchanged"},
    {"card_text": "CSV EXPORT", "from_column": "Building", "to_column": "Review", "change_type": "moved"},
    {"card_text": "LOAD TEST", "from_column": "", "to_column": "Queued", "change_type": "new_card"},
    {"card_text": "LOGIN HOOK", "from_column": "Review", "to_column": "Shipped", "change_type": "moved"},
    {"card_text": "OCR PROMPT", "from_column": "Building", "to_column": "Building", "change_type": "unchanged"},
    {"card_text": "OLD MOCKS", "from_column": "Review", "to_column": "", "change_type": "removed_card"},
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_record(record: object, seen_cards: set[str]) -> None:
    assert_true(isinstance(record, dict), f"Each NDJSON line must be a JSON object, got {type(record).__name__}.")

    expected_keys = {"card_text", "from_column", "to_column", "change_type"}
    assert_true(set(record.keys()) == expected_keys, f"Record keys mismatch: {record}")

    card_text = record["card_text"]
    from_column = record["from_column"]
    to_column = record["to_column"]
    change_type = record["change_type"]

    assert_true(isinstance(card_text, str) and card_text != "", f"card_text must be a non-empty string: {record}")
    assert_true(card_text not in seen_cards, f"Duplicate card_text found: {card_text}")
    seen_cards.add(card_text)

    assert_true(isinstance(from_column, str), f"from_column must be a string: {record}")
    assert_true(isinstance(to_column, str), f"to_column must be a string: {record}")
    assert_true(from_column in ALLOWED_COLUMNS or from_column == "", f"Invalid from_column: {record}")
    assert_true(to_column in ALLOWED_COLUMNS or to_column == "", f"Invalid to_column: {record}")

    allowed_change_types = {"unchanged", "moved", "new_card", "removed_card"}
    assert_true(change_type in allowed_change_types, f"Invalid change_type: {record}")

    if change_type == "unchanged":
        assert_true(from_column != "" and from_column == to_column, f"unchanged record is invalid: {record}")
    elif change_type == "moved":
        assert_true(from_column != "" and to_column != "" and from_column != to_column, f"moved record is invalid: {record}")
    elif change_type == "new_card":
        assert_true(from_column == "" and to_column != "", f"new_card record is invalid: {record}")
    elif change_type == "removed_card":
        assert_true(from_column != "" and to_column == "", f"removed_card record is invalid: {record}")


def main() -> None:
    assert_true(OUTPUT_FILE.exists(), "Output file /app/workspace/kanban_status_diff.ndjson was not created.")

    text = OUTPUT_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert_true(lines, "Output NDJSON is empty.")
    assert_true(all(line.strip() for line in lines), "Output NDJSON must not contain blank lines.")

    records = []
    seen_cards: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"Line {line_number} is not valid JSON: {exc}") from exc
        validate_record(record, seen_cards)
        records.append(record)

    actual_order = [record["card_text"] for record in records]
    expected_order = sorted(actual_order)
    assert_true(actual_order == expected_order, f"Records must be sorted by card_text. Actual order: {actual_order}")

    assert_true(records == EXPECTED_RECORDS, f"Output records do not match the oracle.\nActual: {records}\nExpected: {EXPECTED_RECORDS}")


if __name__ == "__main__":
    main()
