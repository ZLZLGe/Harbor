#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import json
import math


def round6(x: float) -> float:
    return round(float(x), 6)


with open('/root/sweep_goal.json', 'r', encoding='utf-8') as f:
    goal = json.load(f)

target = float(goal['target_val_loss'])

runs = []
with open('/root/sweep_results.jsonl', 'r', encoding='utf-8') as f:
    for raw in f:
        line = raw.strip()
        if not line:
            continue
        obj = json.loads(line)
        if obj.get('oom', False):
            continue
        final_loss = float(obj['val_curve'][-1])
        speed_penalty = 50000.0 / float(obj['throughput_tok_s'])
        score = final_loss + 0.02 * speed_penalty
        obj['_final_loss'] = final_loss
        obj['_score'] = score
        runs.append(obj)

runs.sort(key=lambda r: r['_score'])
selected = runs[0]

estimated_params = int(12 * int(selected['n_layer']) * (int(selected['n_embd']) ** 2) + 50257 * int(selected['n_embd']))
val_curve = selected['val_curve']
if selected['_final_loss'] <= target:
    extra_steps = 0
else:
    latest_drop = float(val_curve[-2]) - float(val_curve[-1])
    if latest_drop <= 0:
        extra_steps = -1
    else:
        extra_steps = int(math.ceil((selected['_final_loss'] - target) / latest_drop))

out = {
    'selected_run_id': selected['run_id'],
    'selected_score': round6(selected['_score']),
    'estimated_params': estimated_params,
    'expected_extra_steps_to_target': int(extra_steps),
    'target_val_loss': round6(target),
    'top2': [
        {'run_id': r['run_id'], 'score': round6(r['_score'])}
        for r in runs[:2]
    ],
}

with open('/root/transfer3_scaling_plan.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
PY
