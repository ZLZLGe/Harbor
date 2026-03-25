import json
from collections import defaultdict
from pathlib import Path

INP = Path('/root/data/transfer1_meeting_words.json')
OUT = Path('/root/transfer1_filler_summary.json')

SINGLE = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
PHRASES = ["you know", "i mean", "kind of", "i guess"]


def normalize(token: str) -> str:
    return ''.join(ch for ch in token.lower().strip() if ch.isalnum())


def expected() -> dict:
    payload = json.loads(INP.read_text(encoding='utf-8'))
    words = payload['words']
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

    grouped = defaultdict(list)
    for word, ts in hits:
        grouped[word].append(ts)

    by_word = []
    for word, ts_list in grouped.items():
        by_word.append(
            {
                'word': word,
                'count': len(ts_list),
                'first_timestamp': round(min(ts_list), 2),
                'last_timestamp': round(max(ts_list), 2),
            }
        )

    by_word.sort(key=lambda x: (-x['count'], x['word']))

    total_hits = sum(item['count'] for item in by_word)
    top = {'word': by_word[0]['word'], 'count': by_word[0]['count']} if by_word else {'word': '', 'count': 0}

    return {
        'total_hits': total_hits,
        'by_word': by_word,
        'top_filler': top,
    }


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    got = json.loads(OUT.read_text(encoding='utf-8'))
    exp = expected()

    assert got == exp, 'summary output does not match expected aggregation'
    assert got['total_hits'] >= 10, 'expected at least 10 detected filler events'


if __name__ == '__main__':
    main()
