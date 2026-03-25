import json
from pathlib import Path

INP = Path('/root/data/similar_transcript_words.json')
OUT = Path('/root/similar_annotations.json')

SINGLE = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
PHRASES = ["you know", "i mean", "kind of", "i guess"]


def normalize(token: str) -> str:
    return ''.join(ch for ch in token.lower().strip() if ch.isalnum())


def expected() -> list[dict]:
    words = json.loads(INP.read_text(encoding='utf-8'))
    norm = [normalize(item['word']) for item in words]

    annotations = []
    for i, item in enumerate(words):
        w = norm[i]
        if w in SINGLE:
            annotations.append({'word': w, 'timestamp': round(float(item['start']), 2)})

    for i in range(len(words) - 1):
        phrase = f"{norm[i]} {norm[i+1]}"
        if phrase in PHRASES:
            annotations.append({'word': phrase, 'timestamp': round(float(words[i]['start']), 2)})

    annotations.sort(key=lambda x: x['timestamp'])
    seen = set()
    unique = []
    for item in annotations:
        key = (item['word'], item['timestamp'])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    got = json.loads(OUT.read_text(encoding='utf-8'))
    assert isinstance(got, list), 'output must be a JSON array'

    exp = expected()
    assert got == exp, 'annotations do not match expected filler detections'
    assert len(got) >= 12, 'too few detections; transcript should yield at least 12 events'


if __name__ == '__main__':
    main()
