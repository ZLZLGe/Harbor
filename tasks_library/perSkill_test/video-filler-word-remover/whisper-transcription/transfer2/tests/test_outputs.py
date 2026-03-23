import json
from collections import Counter
from pathlib import Path

INP = Path('/root/data/transfer2_support_turns.json')
OUT = Path('/root/transfer2_window_report.json')

SINGLE = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
PHRASES = ["you know", "i mean", "kind of", "i guess"]
WINDOW = 30


def normalize(token: str) -> str:
    return ''.join(ch for ch in token.lower().strip() if ch.isalnum())


def expected() -> dict:
    turns = json.loads(INP.read_text(encoding='utf-8'))
    words = []
    for turn in turns:
        words.extend(turn['words'])
    words.sort(key=lambda x: x['start'])

    norm = [normalize(item['word']) for item in words]

    hits = []
    for i, item in enumerate(words):
        w = norm[i]
        if w in SINGLE:
            hits.append((w, round(float(item['start']), 2)))

    for i in range(len(words) - 1):
        phrase = f"{norm[i]} {norm[i+1]}"
        if phrase in PHRASES:
            hits.append((phrase, round(float(words[i]['start']), 2)))

    hits = sorted(set(hits), key=lambda x: x[1])
    max_ts = max((ts for _, ts in hits), default=0.0)
    num_windows = int(max_ts // WINDOW) + 1

    windows = []
    for idx in range(num_windows):
        start = idx * WINDOW
        end = start + WINDOW
        in_window = [(word, ts) for word, ts in hits if start <= ts < end]
        count = len(in_window)
        density = round(count * 2.0, 2)
        if count == 0:
            dominant = ''
        else:
            counter = Counter(word for word, _ in in_window)
            top = max(counter.values())
            dominant = sorted(word for word, c in counter.items() if c == top)[0]

        windows.append(
            {
                'window_start': start,
                'window_end': end,
                'filler_count': count,
                'density_per_minute': density,
                'dominant_filler': dominant,
            }
        )

    peak_count = max((item['filler_count'] for item in windows), default=0)
    peak_start = min((item['window_start'] for item in windows if item['filler_count'] == peak_count), default=0)

    return {
        'window_size_seconds': WINDOW,
        'windows': windows,
        'peak_window_start': peak_start,
        'peak_window_count': peak_count,
    }


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    got = json.loads(OUT.read_text(encoding='utf-8'))
    exp = expected()

    assert got == exp, 'window report mismatch'
    assert len(got['windows']) >= 3, 'expected at least three analysis windows'


if __name__ == '__main__':
    main()
