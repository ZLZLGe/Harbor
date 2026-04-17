import json
import re
from collections import Counter
from pathlib import Path

INPUT_PATH = Path("/root/data/run_logs.jsonl")
OUT_MD = Path("/root/transfer3_batch_summary.md")
OUT_JSONL = Path("/root/transfer3_retry_queue.jsonl")
MAX_CHARS = 1300
ALLOWED_VOICES = {
    "21m00Tcm4TlvDq8ikWAM",
    "EXAVITQu4vr4xnSDxMaL",
    "ErXwobaYiN019PkySvjV",
    "TxGEqnHWrfWFTfGW9XjX",
}
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sentence_chunk(text: str, limit: int) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(sentence), limit):
                part = sentence[i : i + limit].strip()
                if part:
                    chunks.append(part)
            continue
        if not current:
            current = sentence
            continue
        if len(current) + 1 + len(sentence) <= limit:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def expected_outputs() -> tuple[list[dict], str]:
    rows = []
    for line in INPUT_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    failures_by_status: Counter[int] = Counter()
    voice_jobs: Counter[str] = Counter()
    voice_failed: Counter[str] = Counter()
    retry_rows = []
    max_chunk_length = 0

    for row in rows:
        job_id = str(row.get("job_id", "")).strip()
        voice_id = str(row.get("voice_id", "")).strip()
        if voice_id not in ALLOWED_VOICES:
            voice_id = DEFAULT_VOICE
        status_code = int(row.get("status_code", 0))
        cleaned = clean_text(str(row.get("text", "")))

        voice_jobs[voice_id] += 1
        if status_code != 200:
            failures_by_status[status_code] += 1
            voice_failed[voice_id] += 1
            chunks = sentence_chunk(cleaned, MAX_CHARS)
            for idx, chunk in enumerate(chunks, start=1):
                max_chunk_length = max(max_chunk_length, len(chunk))
                retry_rows.append(
                    {
                        "retry_id": f"{job_id}-{idx}",
                        "voice_id": voice_id,
                        "url": f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                        "headers": {
                            "xi-api-key": "${ELEVENLABS_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        "body": {
                            "text": chunk,
                            "model_id": "eleven_turbo_v2_5",
                            "voice_settings": {
                                "stability": 0.5,
                                "similarity_boost": 0.5,
                            },
                        },
                    }
                )

    lines = []
    lines.append("# ElevenLabs Batch Summary")
    lines.append("")
    lines.append(f"- Total jobs: {len(rows)}")
    lines.append(f"- Successful jobs: {sum(1 for r in rows if int(r.get('status_code', 0)) == 200)}")
    lines.append(f"- Failed jobs: {sum(1 for r in rows if int(r.get('status_code', 0)) != 200)}")
    lines.append("")
    lines.append("## Failures by Status")
    lines.append("| status_code | count |")
    lines.append("|---:|---:|")
    for status in sorted(failures_by_status):
        lines.append(f"| {status} | {failures_by_status[status]} |")
    lines.append("")
    lines.append("## Voice Utilization")
    lines.append("| voice_id | jobs | failed |")
    lines.append("|---|---:|---:|")
    for voice in sorted(voice_jobs):
        lines.append(f"| {voice} | {voice_jobs[voice]} | {voice_failed[voice]} |")
    lines.append("")
    lines.append("## Retry Queue")
    lines.append(f"- Retry request lines: {len(retry_rows)}")
    lines.append(f"- Max chunk length: {max_chunk_length}")
    markdown = "\n".join(lines) + "\n"

    return retry_rows, markdown


def test_outputs() -> None:
    assert OUT_MD.exists(), f"missing output: {OUT_MD}"
    assert OUT_JSONL.exists(), f"missing output: {OUT_JSONL}"

    actual_retry_lines = [line.strip() for line in OUT_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]
    actual_retry = [json.loads(line) for line in actual_retry_lines]

    expected_retry, expected_markdown = expected_outputs()
    assert actual_retry == expected_retry, "retry queue mismatch"

    actual_markdown = OUT_MD.read_text(encoding="utf-8")
    assert actual_markdown == expected_markdown, "summary markdown mismatch"


if __name__ == "__main__":
    test_outputs()
    print("transfer3 checks passed")
