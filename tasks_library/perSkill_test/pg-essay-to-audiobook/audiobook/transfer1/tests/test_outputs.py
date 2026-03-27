import csv
import json
import re
import wave
from pathlib import Path

AUDIO_PATH = Path('/root/transfer1_city_briefing.wav')
CSV_PATH = Path('/root/transfer1_chapter_stats.csv')


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"^\s*#+\s+.*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, max_chars: int = 180) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks: list[str] = []
    current = ""
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


def expected_rows() -> list[dict[str, str]]:
    playlist = json.loads(Path('/root/data/playlist_order.json').read_text(encoding='utf-8'))['items']
    rows = []
    for item in playlist:
        title = item['title']
        raw = Path('/root/data', item['file']).read_text(encoding='utf-8')
        cleaned = clean_markdown(raw)
        narration = f"Briefing: {title}. {cleaned}"
        rows.append({
            'chapter_title': title,
            'char_count': str(len(cleaned)),
            'chunk_count': str(len(chunk_text(narration, max_chars=180))),
        })
    return rows


def test_outputs() -> None:
    assert AUDIO_PATH.exists(), f'missing audio output: {AUDIO_PATH}'
    assert CSV_PATH.exists(), f'missing chapter csv: {CSV_PATH}'

    with CSV_PATH.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    assert rows == expected_rows(), 'chapter stats do not match expected values'

    assert AUDIO_PATH.stat().st_size > 20000, 'audio output is unexpectedly small'
    assert wav_duration(AUDIO_PATH) > 8.0, 'audio duration too short'


if __name__ == '__main__':
    test_outputs()
    print('transfer1 checks passed')
