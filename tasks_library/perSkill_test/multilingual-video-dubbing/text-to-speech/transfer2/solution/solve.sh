#!/bin/bash
set -euo pipefail

mkdir -p /outputs/prompts /tmp

python3 - <<'PY'
import json
import re
import subprocess
from pathlib import Path

PROMPTS = Path("/root/prompts.json")
TARGET_LANG = Path("/root/target_language.txt")
OUT_DIR = Path("/outputs/prompts")
MANIFEST = Path("/outputs/prompt_manifest.json")


def run(cmd):
    subprocess.check_call(cmd)


def duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def loudness(path: Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        text=True,
        capture_output=True,
        check=False,
    )
    matches = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", proc.stderr)
    return float(matches[-1]) if matches else -70.0


def normalize(input_path: Path, output_path: Path, target: float = -23.0):
    tmp = Path("/tmp/norm.wav")
    g1 = target - loudness(input_path)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(input_path), "-af", f"volume={g1}dB", "-ar", "48000", "-ac", "1", str(tmp)])
    g2 = target - loudness(tmp)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-af", f"volume={g2}dB", "-ar", "48000", "-ac", "1", str(output_path)])


def voice_for(lang: str) -> str:
    mapping = {"en": "en-us", "es": "es", "fr": "fr-fr", "de": "de", "ja": "ja", "zh": "zh"}
    code = lang.strip().lower()
    return mapping.get(code, mapping.get(code.split("-")[0], "en-us"))


def atempo_chain(speed: float) -> str:
    parts = []
    remain = speed
    while remain > 2.0:
        parts.append("atempo=2.0")
        remain /= 2.0
    while remain < 0.5:
        parts.append("atempo=0.5")
        remain /= 0.5
    parts.append(f"atempo={remain:.6f}")
    return ",".join(parts)


items = json.loads(PROMPTS.read_text(encoding="utf-8"))
voice = voice_for(TARGET_LANG.read_text(encoding="utf-8").strip())
results = []

for item in items:
    item_id = item["id"]
    text = item["text"]
    target_duration = float(item["target_duration_sec"])
    raw = Path(f"/tmp/{item_id}_raw.wav")
    ready = Path(f"/tmp/{item_id}_ready.wav")
    aligned = Path(f"/tmp/{item_id}_aligned.wav")
    output_wav = OUT_DIR / f"{item_id}.wav"

    run(["espeak-ng", "-v", voice, "-s", "155", "-w", str(raw), text])
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
        "-af", "highpass=f=20,lowpass=f=16000,afade=t=in:st=0:d=0.05",
        "-ar", "48000", "-ac", "1", "/tmp/tmp_pre.wav"
    ])
    d0 = duration(Path("/tmp/tmp_pre.wav"))
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/tmp_pre.wav",
        "-af", f"afade=t=out:st={max(0.0, d0 - 0.05):.3f}:d=0.05",
        "-ar", "48000", "-ac", "1", str(ready)
    ])

    d1 = duration(ready)
    mode = "rate_adjust"
    if d1 > target_duration + 0.02:
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(ready),
            "-af", atempo_chain(d1 / target_duration), "-ar", "48000", "-ac", "1", str(aligned)
        ])
    elif d1 < target_duration - 0.02:
        mode = "pad_silence"
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(ready),
            "-af", f"apad=pad_dur={target_duration - d1:.3f}", "-ar", "48000", "-ac", "1", str(aligned)
        ])
    else:
        run(["cp", str(ready), str(aligned)])

    if duration(aligned) > target_duration + 0.02:
        mode = "trim"
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(aligned),
            "-af", f"atrim=0:{target_duration:.3f}", "-ar", "48000", "-ac", "1", "/tmp/tmp_trim.wav"
        ])
        run(["mv", "/tmp/tmp_trim.wav", str(aligned)])

    normalize(aligned, output_wav, -23.0)

    actual = duration(output_wav)
    drift = actual - target_duration
    results.append(
        {
            "id": item_id,
            "file": str(output_wav),
            "target_duration_sec": target_duration,
            "actual_duration_sec": actual,
            "drift_sec": drift,
            "duration_control": mode,
            "lufs": loudness(output_wav),
        }
    )

payload = {
    "target_language": TARGET_LANG.read_text(encoding="utf-8").strip(),
    "audio_sample_rate_hz": 48000,
    "audio_channels": 1,
    "items": results,
}
MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
