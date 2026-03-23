import json
from pathlib import Path

INP = Path('/root/data/transfer3_panel_segments.json')
OUT = Path('/root/transfer3_clip_plan.json')

SINGLE = {"um", "uh", "hum", "hmm", "mhm", "like", "yeah", "so", "basically", "well", "okay"}
PHRASES = ["you know", "i mean", "kind of", "i guess"]
LEAD_IN = 0.05
MERGE_GAP = 0.1
WORD_DURATIONS = {
    'uh': 0.30,
    'um': 0.40,
    'hum': 0.60,
    'hmm': 0.60,
    'mhm': 0.55,
    'like': 0.30,
    'yeah': 0.35,
    'so': 0.25,
    'well': 0.35,
    'okay': 0.40,
    'basically': 0.55,
    'you know': 0.55,
    'i mean': 0.50,
    'kind of': 0.50,
    'i guess': 0.50,
}
DEFAULT_DURATION = 0.40


def normalize(token: str) -> str:
    return ''.join(ch for ch in token.lower().strip() if ch.isalnum())


def expected() -> dict:
    payload = json.loads(INP.read_text(encoding='utf-8'))
    words = []
    for segment in payload['segments']:
        words.extend(segment['words'])
    words.sort(key=lambda x: x['start'])

    norm = [normalize(item['word']) for item in words]

    hits = []
    for i, item in enumerate(words):
        w = norm[i]
        if w in SINGLE:
            hits.append({'word': w, 'timestamp': round(float(item['start']), 2)})

    for i in range(len(words) - 1):
        phrase = f"{norm[i]} {norm[i+1]}"
        if phrase in PHRASES:
            hits.append({'word': phrase, 'timestamp': round(float(words[i]['start']), 2)})

    seen = set()
    ordered_hits = []
    for hit in sorted(hits, key=lambda x: x['timestamp']):
        key = (hit['word'], hit['timestamp'])
        if key in seen:
            continue
        seen.add(key)
        ordered_hits.append(hit)

    raw = []
    for hit in ordered_hits:
        ts = hit['timestamp']
        duration = WORD_DURATIONS.get(hit['word'], DEFAULT_DURATION)
        raw.append({'start': max(0.0, ts - LEAD_IN), 'end': ts + duration, 'trigger': hit['word']})

    merged = []
    for clip in raw:
        if not merged:
            merged.append(clip)
            continue
        prev = merged[-1]
        if clip['start'] <= prev['end'] + MERGE_GAP:
            prev['end'] = max(prev['end'], clip['end'])
        else:
            merged.append(clip)

    clips = []
    for clip in merged:
        start = round(clip['start'], 2)
        end = round(clip['end'], 2)
        clips.append(
            {
                'start': start,
                'end': end,
                'duration': round(end - start, 2),
                'trigger': clip['trigger'],
            }
        )

    total_duration = round(sum(item['duration'] for item in clips), 2)
    return {
        'clip_parameters': {
            'lead_in_seconds': LEAD_IN,
            'merge_gap_seconds': MERGE_GAP,
            'word_durations': WORD_DURATIONS,
        },
        'clips': clips,
        'total_clips': len(clips),
        'total_duration_seconds': total_duration,
    }


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    got = json.loads(OUT.read_text(encoding='utf-8'))
    exp = expected()

    assert got == exp, 'clip plan mismatch'
    assert got['total_clips'] >= 4, 'expected at least four merged clips'


if __name__ == '__main__':
    main()
