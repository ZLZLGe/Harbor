import json
from pathlib import Path

OUTPUT = Path('/outputs/syntax_mapping_reference.json')

EXPECTED = [
    {
        "case_id": "S1",
        "category": "variable_declaration",
        "python": "x = 5",
        "scala": "val x = 5"
    },
    {
        "case_id": "S2",
        "category": "typed_variable",
        "python": "x: int = 5",
        "scala": "val x: Int = 5"
    },
    {
        "case_id": "S3",
        "category": "tuple_unpacking",
        "python": "x, y = 1, 2",
        "scala": "val (x, y) = (1, 2)"
    },
    {
        "case_id": "S4",
        "category": "conditional_expression",
        "python": "if x > 0: positive elif x < 0: negative else: zero",
        "scala": "val result = if (x > 0) \"positive\" else if (x < 0) \"negative\" else \"zero\""
    },
    {
        "case_id": "S5",
        "category": "range_loop",
        "python": "for i in range(10): print(i)",
        "scala": "for (i <- 0 until 10) println(i)"
    },
    {
        "case_id": "S6",
        "category": "filter_comprehension",
        "python": "evens = [x for x in numbers if x % 2 == 0]",
        "scala": "val evens = numbers.filter(_ % 2 == 0)"
    },
    {
        "case_id": "S7",
        "category": "string_format",
        "python": "f\"Hello, {name}!\"",
        "scala": "s\"Hello, $name!\""
    },
    {
        "case_id": "S8",
        "category": "boolean_operators",
        "python": "ready and not blocked",
        "scala": "ready && !blocked"
    }
]


def test_output_exists() -> None:
    assert OUTPUT.exists(), f"Missing output file: {OUTPUT}"


def test_exact_payload() -> None:
    payload = json.loads(OUTPUT.read_text(encoding='utf-8'))
    assert payload == EXPECTED, "Output JSON does not match expected syntax mapping reference"


if __name__ == '__main__':
    test_output_exists()
    test_exact_payload()
