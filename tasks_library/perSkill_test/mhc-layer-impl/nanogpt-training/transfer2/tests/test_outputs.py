import json
import math
from pathlib import Path

INP = Path('/root/optimizer_runs.json')
OUT = Path('/root/transfer2_optimizer_report.json')


def round6(x: float) -> float:
    return round(float(x), 6)


def pop_std(values):
    m = sum(values) / len(values)
    return (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


def get_lr(step, warmup_steps, max_steps, max_lr, min_lr):
    if step < warmup_steps:
        return max_lr * (step + 1) / warmup_steps
    if step >= max_steps:
        return min_lr
    decay_ratio = (step - warmup_steps) / (max_steps - warmup_steps)
    coeff = 0.5 * (1.0 + math.cos(math.pi * decay_ratio))
    return min_lr + coeff * (max_lr - min_lr)


def compute_expected(data):
    adamw_final = data['adamw']['val_loss'][-1]
    muon_final = data['muon']['val_loss'][-1]
    adamw_std = pop_std(data['adamw']['grad_norm'])
    muon_std = pop_std(data['muon']['grad_norm'])

    if muon_final < adamw_final:
        best = 'muon'
    elif muon_final > adamw_final:
        best = 'adamw'
    else:
        best = 'muon' if muon_std < adamw_std else 'adamw'

    schedule = data['schedule']
    lr_map = {}
    for step in data['checkpoints']:
        lr = get_lr(
            int(step),
            int(schedule['warmup_steps']),
            int(schedule['max_steps']),
            float(schedule['max_lr']),
            float(schedule['min_lr']),
        )
        lr_map[str(step)] = round6(lr)

    return {
        'scenario': data['scenario'],
        'adamw_final_loss': round6(adamw_final),
        'muon_final_loss': round6(muon_final),
        'adamw_grad_norm_std': round6(adamw_std),
        'muon_grad_norm_std': round6(muon_std),
        'adamw_max_grad_norm': round6(max(data['adamw']['grad_norm'])),
        'muon_max_grad_norm': round6(max(data['muon']['grad_norm'])),
        'best_optimizer': best,
        'lr_checkpoints': lr_map,
    }


def test_output_exists():
    assert OUT.exists(), 'missing /root/transfer2_optimizer_report.json'


def test_optimizer_report_matches_expected():
    with INP.open('r', encoding='utf-8') as f:
        data = json.load(f)
    with OUT.open('r', encoding='utf-8') as f:
        out = json.load(f)

    assert out == compute_expected(data)
