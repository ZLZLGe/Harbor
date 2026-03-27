import json
import re
import wave
from pathlib import Path

AUDIO_PATH = Path('/root/transfer2_training_digest.wav')
JSON_PATH = Path('/root/transfer2_digest.json')


def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def chunk_text(text: str, max_chars: int = 160) -> list[str]:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    chunks: list[str] = []
    current = ''
    for sentence in sentences:
        if not current:
            current = sentence
            continue
        if len(current) + 1 + len(sentence) <= max_chars:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def wav_duration(path: Path) -> float:
    with wave.open(str(path), 'rb') as wf:
        return wf.getnframes() / float(wf.getframerate())


def expected_report() -> dict:
    rows = []
    for line in Path('/root/data/call_snippets.jsonl').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    kept = [r for r in rows if bool(r.get('publish')) and int(r.get('priority', 0)) >= 2]
    kept.sort(key=lambda r: (int(r['session_id']), str(r.get('speaker', ''))))

    sentences = []
    for r in kept:
        sid = int(r['session_id'])
        speaker = str(r.get('speaker', '')).strip()
        text = clean_text(str(r.get('text', '')))
        sentences.append(f"Segment {sid} - {speaker}: {text}.")

    narration = ' '.join(sentences).strip()
    return {
        'included_session_ids': sorted({int(r['session_id']) for r in kept}),
        'segment_count': len(sentences),
        'chunk_count': len(chunk_text(narration, max_chars=160)),
        'total_chars': len(narration),
    }


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f'missing audio output: {AUDIO_PATH}'
    assert JSON_PATH.exists(), f'missing digest json: {JSON_PATH}'

    actual = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    assert actual == expected_report(), 'digest report does not match expected values'

    assert AUDIO_PATH.stat().st_size > 15000, 'audio output is unexpectedly small'
    assert wav_duration(AUDIO_PATH) > 6.0, 'audio duration too short'


if __name__ == '__main__':
    test_outputs()
    print('transfer2 checks passed')
