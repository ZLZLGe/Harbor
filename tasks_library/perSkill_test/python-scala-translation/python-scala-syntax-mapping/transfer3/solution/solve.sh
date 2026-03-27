#!/bin/bash
set -euo pipefail

mkdir -p /outputs

python3 - <<'PY'
import json
from pathlib import Path

answer_key = json.loads(Path('/root/quiz_answer_key.json').read_text(encoding='utf-8'))
attempts = json.loads(Path('/root/quiz_attempts.json').read_text(encoding='utf-8'))

qids = list(answer_key.keys())
total = len(qids)
participants = []

for attempt in attempts:
    name = attempt['participant']
    answers = attempt['answers']
    missed = []
    correct = 0
    for qid in qids:
        if answers.get(qid) == answer_key[qid]:
            correct += 1
        else:
            missed.append(qid)
    accuracy = round((correct / total) * 100, 1)
    participants.append({
        'participant': name,
        'correct': correct,
        'total': total,
        'accuracy_percent': accuracy,
        'missed_case_ids': missed
    })

participants.sort(key=lambda item: (-item['accuracy_percent'], item['participant']))

result = {
    'generated_from': 'quiz_attempts.json',
    'total_questions': total,
    'participants': participants,
    'top_performer': participants[0]['participant'] if participants else ''
}

Path('/outputs/syntax_mapping_scoreboard.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
PY
