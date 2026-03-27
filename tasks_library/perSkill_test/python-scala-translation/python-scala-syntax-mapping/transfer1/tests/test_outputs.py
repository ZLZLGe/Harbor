import csv
from pathlib import Path

OUTPUT = Path('/outputs/syntax_mapping_audit.csv')

EXPECTED = [
    {
        'case_id': 'A1',
        'python': 'x = 5',
        'proposed_scala': 'val x = 5',
        'is_correct': 'true',
        'correct_scala': 'val x = 5',
    },
    {
        'case_id': 'A2',
        'python': 'x: int = 5',
        'proposed_scala': 'var x: int = 5',
        'is_correct': 'false',
        'correct_scala': 'val x: Int = 5',
    },
    {
        'case_id': 'A3',
        'python': 'for i in range(10): print(i)',
        'proposed_scala': 'for (i <- 0 to 9) println(i)',
        'is_correct': 'false',
        'correct_scala': 'for (i <- 0 until 10) println(i)',
    },
    {
        'case_id': 'A4',
        'python': 'f"Value: {x:.2f}"',
        'proposed_scala': 'f"Value: $x%.2f"',
        'is_correct': 'true',
        'correct_scala': 'f"Value: $x%.2f"',
    },
    {
        'case_id': 'A5',
        'python': 'user_active and not suspended',
        'proposed_scala': 'user_active && !suspended',
        'is_correct': 'true',
        'correct_scala': 'user_active && !suspended',
    },
    {
        'case_id': 'A6',
        'python': 'evens = [x for x in numbers if x % 2 == 0]',
        'proposed_scala': 'val evens = numbers.map(_ * 2)',
        'is_correct': 'false',
        'correct_scala': 'val evens = numbers.filter(_ % 2 == 0)',
    },
]


def test_output_exists() -> None:
    assert OUTPUT.exists(), f'Missing output file: {OUTPUT}'


def test_csv_payload() -> None:
    with OUTPUT.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert rows == EXPECTED, 'Audit CSV rows do not match expected judgments'


if __name__ == '__main__':
    test_output_exists()
    test_csv_payload()
