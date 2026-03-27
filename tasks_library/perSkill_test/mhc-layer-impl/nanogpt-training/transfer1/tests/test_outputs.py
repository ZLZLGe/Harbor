import json
from pathlib import Path

INP = Path('/root/token_shards.json')
OUT = Path('/root/transfer1_loader_report.json')


def compute_expected(data):
    tokens = []
    for shard in data['shards']:
        tokens.extend(shard)

    block_size = int(data['block_size'])
    batch_size = int(data['batch_size'])
    offsets = list(data['offsets'])

    used_tokens = set()
    batches = []
    for offset in offsets:
        x_rows = []
        y_rows = []
        for i in range(batch_size):
            start = (offset + i * block_size) % len(tokens)
            window = [tokens[(start + j) % len(tokens)] for j in range(block_size + 1)]
            x = window[:-1]
            y = window[1:]
            x_rows.append(x)
            y_rows.append(y)
            used_tokens.update(x)
        batches.append({'offset': int(offset), 'x': x_rows, 'y': y_rows})

    unique_total = len(set(tokens))
    coverage_ratio = round(len(used_tokens) / unique_total, 6) if unique_total else 0.0

    return {
        'scenario': data['scenario'],
        'num_sequences': len(offsets) * batch_size,
        'unique_token_count': unique_total,
        'coverage_ratio': coverage_ratio,
        'batches': batches,
    }


def test_output_exists():
    assert OUT.exists(), 'missing /root/transfer1_loader_report.json'


def test_loader_report_matches_expected():
    with INP.open('r', encoding='utf-8') as f:
        data = json.load(f)
    with OUT.open('r', encoding='utf-8') as f:
        out = json.load(f)

    assert out == compute_expected(data)
