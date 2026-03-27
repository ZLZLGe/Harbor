#!/bin/bash
set -euo pipefail

mkdir -p /outputs/tts_segments /tmp

python3 - <<'PY'
import json
import re
import subprocess
from pathlib import Path

CUE_SRT = Path("/root/cue.srt")
PROMO_TEXT = Path("/root/promo_text.txt")
TARGET_LANG = Path("/root/target_language.txt")
BED_WAV = Path("/root/bed.wav")
SEG_WAV = Path("/outputs/tts_segments/seg_0.wav")
OUT_WAV = Path("/outputs/episode_mix.wav")
OUT_JSON = Path("/outputs/episode_report.json")


def run(cmd):
    subprocess.check_call(cmd)


def duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def parse_ts(ts: str) -> float:
    hh, mm, rest = ts.split(":")
    ss, ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def parse_window(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if "-->" in line:
            left, right = [part.strip() for part in line.split("-->")]
            return parse_ts(left), parse_ts(right)
    raise RuntimeError("cue window missing")


def voice_for(lang: str) -> str:
    mapping = {"en": "en-us", "es": "es", "fr": "fr-fr", "de": "de", "ja": "ja", "zh": "zh"}
    code = lang.strip().lower()
    return mapping.get(code, mapping.get(code.split("-")[0], "en-us"))


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
    l1 = loudness(input_path)
    g1 = target - l1
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(input_path), "-af", f"volume={g1}dB", "-ar", "48000", "-ac", "1", str(tmp)])
    l2 = loudness(tmp)
    g2 = target - l2
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-af", f"volume={g2}dB", "-ar", "48000", "-ac", "1", str(output_path)])


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


start, end = parse_window(CUE_SRT)
win_dur = max(0.05, end - start)
text = PROMO_TEXT.read_text(encoding="utf-8").strip()
voice = voice_for(TARGET_LANG.read_text(encoding="utf-8").strip())

run(["espeak-ng", "-v", voice, "-s", "155", "-w", "/tmp/raw.wav", text])
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/raw.wav",
    "-af", "highpass=f=20,lowpass=f=16000,afade=t=in:st=0:d=0.05",
    "-ar", "48000", "-ac", "1", "/tmp/pre.wav"
])
pre_dur = duration(Path("/tmp/pre.wav"))
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/pre.wav",
    "-af", f"afade=t=out:st={max(0.0, pre_dur - 0.05):.3f}:d=0.05",
    "-ar", "48000", "-ac", "1", "/tmp/ready.wav"
])

ready_dur = duration(Path("/tmp/ready.wav"))
mode = "rate_adjust"
if ready_dur > win_dur + 0.02:
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/ready.wav",
        "-af", atempo_chain(ready_dur / win_dur), "-ar", "48000", "-ac", "1", "/tmp/aligned.wav"
    ])
elif ready_dur < win_dur - 0.02:
    mode = "pad_silence"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/ready.wav",
        "-af", f"apad=pad_dur={win_dur - ready_dur:.3f}", "-ar", "48000", "-ac", "1", "/tmp/aligned.wav"
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

normalize(Path("/tmp/aligned.wav"), SEG_WAV, -23.0)

start_ms = int(round(start * 1000.0))
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", str(BED_WAV), "-i", str(SEG_WAV),
    "-filter_complex", f"[0:a]volume=0.75[bg];[1:a]adelay={start_ms}|{start_ms}[vo];[bg][vo]amix=inputs=2:duration=first:dropout_transition=0[m]",
    "-map", "[m]", "-ar", "48000", "-ac", "1", "/tmp/mix.wav"
])

normalize(Path("/tmp/mix.wav"), OUT_WAV, -23.0)

placed_end = start + duration(SEG_WAV)
payload = {
    "target_language": TARGET_LANG.read_text(encoding="utf-8").strip(),
    "audio_sample_rate_hz": 48000,
    "audio_channels": 1,
    "measured_lufs": loudness(OUT_WAV),
    "speech_segments": [
        {
            "window_start_sec": start,
            "window_end_sec": end,
            "placed_start_sec": start,
            "placed_end_sec": placed_end,
            "window_duration_sec": win_dur,
            "tts_duration_sec": duration(SEG_WAV),
            "drift_sec": placed_end - end,
            "duration_control": mode,
        }
    ],
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
