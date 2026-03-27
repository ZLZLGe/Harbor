import csv
import re
import wave
from pathlib import Path

AUDIO_PATH = Path('/root/transfer3_casefile_audio.wav')
CUES_PATH = Path('/root/transfer3_cues.txt')


def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def chunk_text(text: str, max_chars: int = 200) -> list[str]:
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


def expected_cues_and_chunks() -> tuple[list[str], int]:
    rows = []
    with Path('/root/data/casefile_fragments.csv').open(newline='', encoding='utf-8') as f:
        rows.extend(csv.DictReader(f))

    rows.sort(key=lambda r: (str(r['section']), int(r['rank'])))

    kept = []
    seen = set()
    for row in rows:
        cleaned = clean_text(str(row['text']))
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append((str(row['section']), cleaned))

    narration_parts = []
    cues = []
    current_section = None
    for idx, (section, cleaned) in enumerate(kept, start=1):
        if section != current_section:
            narration_parts.append(f"Section {section}.")
            current_section = section
        narration_parts.append(f"{section}: {cleaned}.")
        cues.append(f"{idx}|{section}|{len(cleaned)}")

    narration = ' '.join(narration_parts).strip()
    return cues, len(chunk_text(narration, max_chars=200))


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f'missing audio output: {AUDIO_PATH}'
    assert CUES_PATH.exists(), f'missing cue file: {CUES_PATH}'

    actual_cues = [line.strip() for line in CUES_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]
    expected_cues, expected_chunk_count = expected_cues_and_chunks()
    assert actual_cues == expected_cues, 'cue lines do not match expected values'

    assert len(actual_cues) >= 4, 'unexpectedly low cue count'
    assert expected_chunk_count >= 3, 'expected chunk count sanity check failed'
    assert AUDIO_PATH.stat().st_size > 18000, 'audio output is unexpectedly small'
    assert wav_duration(AUDIO_PATH) > 7.0, 'audio duration too short'


if __name__ == '__main__':
    test_outputs()
    print('transfer3 checks passed')
