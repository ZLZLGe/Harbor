import json
from pathlib import Path

OUTPUT = Path('/outputs/syntax_mapping_scoreboard.json')

EXPECTED = {
    'generated_from': 'quiz_attempts.json',
    'total_questions': 5,
    'participants': [
        {
            'participant': 'li',
            'correct': 5,
            'total': 5,
            'accuracy_percent': 100.0,
            'missed_case_ids': []
        },
        {
            'participant': 'alex',
            'correct': 4,
            'total': 5,
            'accuracy_percent': 80.0,
            'missed_case_ids': ['Q3']
        },
        {
            'participant': 'mia',
            'correct': 2,
            'total': 5,
            'accuracy_percent': 40.0,
            'missed_case_ids': ['Q1', 'Q4', 'Q5']
        }
    ],
    'top_performer': 'li'
}


def test_output_exists() -> None:
    assert OUTPUT.exists(), f'Missing output file: {OUTPUT}'


def test_scoreboard_payload() -> None:
    payload = json.loads(OUTPUT.read_text(encoding='utf-8'))
    assert payload == EXPECTED, 'Scoreboard JSON does not match expected result'


if __name__ == '__main__':
    test_output_exists()
    test_scoreboard_payload()
