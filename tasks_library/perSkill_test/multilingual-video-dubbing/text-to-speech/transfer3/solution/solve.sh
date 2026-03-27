#!/bin/bash
set -euo pipefail

mkdir -p /outputs/tts_segments /tmp

python3 - <<'PY'
import json
import re
import subprocess
from pathlib import Path

WINDOW = Path("/root/window.json")
TEXT = Path("/root/narration.txt")
TARGET = Path("/root/target_language.txt")
AMBIENT = Path("/root/ambient.wav")
SEG = Path("/outputs/tts_segments/seg_0.wav")
MIX = Path("/outputs/kiosk_mix.wav")
REPORT = Path("/outputs/kiosk_report.json")


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


window = json.loads(WINDOW.read_text(encoding="utf-8"))
start = float(window["window_start_sec"])
end = float(window["window_end_sec"])
win_dur = max(0.05, end - start)
voice = voice_for(TARGET.read_text(encoding="utf-8").strip())

run(["espeak-ng", "-v", voice, "-s", "155", "-w", "/tmp/raw.wav", TEXT.read_text(encoding="utf-8").strip()])
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/raw.wav",
    "-af", "highpass=f=20,lowpass=f=16000,afade=t=in:st=0:d=0.05",
    "-ar", "48000", "-ac", "1", "/tmp/pre.wav"
])
d0 = duration(Path("/tmp/pre.wav"))
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/pre.wav",
    "-af", f"afade=t=out:st={max(0.0, d0 - 0.05):.3f}:d=0.05",
    "-ar", "48000", "-ac", "1", "/tmp/ready.wav"
])

ready = duration(Path("/tmp/ready.wav"))
mode = "rate_adjust"
if ready > win_dur + 0.02:
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/ready.wav",
        "-af", atempo_chain(ready / win_dur), "-ar", "48000", "-ac", "1", "/tmp/aligned.wav"
    ])
elif ready < win_dur - 0.02:
    mode = "pad_silence"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/ready.wav",
        "-af", f"apad=pad_dur={win_dur - ready:.3f}", "-ar", "48000", "-ac", "1", "/tmp/aligned.wav"
    ])
else:
    run(["cp", "/tmp/ready.wav", "/tmp/aligned.wav"])

if duration(Path("/tmp/aligned.wav")) > win_dur + 0.02:
    mode = "trim"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/aligned.wav",
        "-af", f"atrim=0:{win_dur:.3f}", "-ar", "48000", "-ac", "1", "/tmp/aligned_trim.wav"
    ])
    run(["mv", "/tmp/aligned_trim.wav", "/tmp/aligned.wav"])

normalize(Path("/tmp/aligned.wav"), SEG, -23.0)

start_ms = int(round(start * 1000.0))
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", str(AMBIENT), "-i", str(SEG),
    "-filter_complex", f"[0:a]volume=0.8[bg];[1:a]adelay={start_ms}|{start_ms}[vo];[bg][vo]amix=inputs=2:duration=first:dropout_transition=0[m]",
    "-map", "[m]", "-ar", "48000", "-ac", "1", "/tmp/mix.wav"
])

normalize(Path("/tmp/mix.wav"), MIX, -23.0)
placed_end = start + duration(SEG)

report = {
    "target_language": TARGET.read_text(encoding="utf-8").strip(),
    "audio_sample_rate_hz": 48000,
    "audio_channels": 1,
    "measured_lufs": loudness(MIX),
    "speech_segments": [
        {
            "window_start_sec": start,
            "window_end_sec": end,
            "placed_start_sec": start,
            "placed_end_sec": placed_end,
            "window_duration_sec": win_dur,
            "tts_duration_sec": duration(SEG),
            "drift_sec": placed_end - end,
            "duration_control": mode,
        }
    ],
}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
PY
