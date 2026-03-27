#!/bin/bash
set -euo pipefail

mkdir -p /outputs/tts_segments /tmp

python3 - <<'PY'
import json
import re
import subprocess
from pathlib import Path

SEG_SRT = Path("/root/segments.srt")
TEXT_SRT = Path("/root/reference_target_text.srt")
TARGET_LANG = Path("/root/target_language.txt")
INPUT_MP4 = Path("/root/input.mp4")
SEG_WAV = Path("/outputs/tts_segments/seg_0.wav")
OUTPUT_MP4 = Path("/outputs/dubbed.mp4")
REPORT_JSON = Path("/outputs/report.json")


def run(cmd):
    subprocess.check_call(cmd)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def parse_ts(ts: str) -> float:
    hh, mm, rest = ts.split(":")
    ss, ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def parse_first_window(srt_path: Path):
    for line in srt_path.read_text(encoding="utf-8").splitlines():
        if "-->" in line:
            left, right = [part.strip() for part in line.split("-->")]
            return parse_ts(left), parse_ts(right)
    raise RuntimeError("No subtitle window found")


def extract_srt_text(srt_path: Path) -> str:
    lines = []
    for line in srt_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.isdigit() or "-->" in stripped:
            continue
        lines.append(stripped)
    if not lines:
        raise RuntimeError("No narration text found")
    return " ".join(lines)


def resolve_voice(lang_code: str) -> str:
    mapping = {
        "en": "en-us",
        "es": "es",
        "fr": "fr-fr",
        "de": "de",
        "it": "it",
        "ja": "ja",
        "zh": "zh",
    }
    code = lang_code.strip().lower()
    if code in mapping:
        return mapping[code]
    prefix = code.split("-")[0]
    return mapping.get(prefix, "en-us")


def measure_lufs(path: Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        text=True,
        capture_output=True,
        check=False,
    )
    matches = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", proc.stderr)
    if not matches:
        return -70.0
    return float(matches[-1])


def normalize_to_lufs(input_path: Path, output_path: Path, target_lufs: float = -23.0):
    first = Path("/tmp/norm_first.wav")
    current = measure_lufs(input_path)
    gain_1 = target_lufs - current
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(input_path), "-af", f"volume={gain_1}dB", "-ar", "48000", "-ac", "1", str(first)])
    current_2 = measure_lufs(first)
    gain_2 = target_lufs - current_2
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(first), "-af", f"volume={gain_2}dB", "-ar", "48000", "-ac", "1", str(output_path)])


def atempo_filter(speed: float) -> str:
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


start_sec, end_sec = parse_first_window(SEG_SRT)
window_dur = max(0.05, end_sec - start_sec)
text = extract_srt_text(TEXT_SRT)
lang_code = TARGET_LANG.read_text(encoding="utf-8").strip()
voice = resolve_voice(lang_code)

run(["espeak-ng", "-v", voice, "-s", "155", "-w", "/tmp/raw.wav", text])

run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/raw.wav",
    "-af", "highpass=f=20,lowpass=f=16000,afade=t=in:st=0:d=0.05",
    "-ar", "48000", "-ac", "1", "/tmp/clean.wav"
])

clean_dur = ffprobe_duration(Path("/tmp/clean.wav"))
fade_out_start = max(0.0, clean_dur - 0.05)
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/clean.wav",
    "-af", f"afade=t=out:st={fade_out_start:.3f}:d=0.05",
    "-ar", "48000", "-ac", "1", "/tmp/ready.wav"
])

ready_dur = ffprobe_duration(Path("/tmp/ready.wav"))
duration_control = "rate_adjust"
if ready_dur > window_dur + 0.02:
    speed = ready_dur / window_dur
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/ready.wav",
        "-af", atempo_filter(speed), "-ar", "48000", "-ac", "1", "/tmp/aligned.wav"
    ])
elif ready_dur < window_dur - 0.02:
    duration_control = "pad_silence"
    pad_dur = window_dur - ready_dur
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/ready.wav",
        "-af", f"apad=pad_dur={pad_dur:.3f}", "-ar", "48000", "-ac", "1", "/tmp/aligned.wav"
    ])
else:
    run(["cp", "/tmp/ready.wav", "/tmp/aligned.wav"])

aligned_dur = ffprobe_duration(Path("/tmp/aligned.wav"))
if aligned_dur > window_dur + 0.02:
    duration_control = "trim"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/aligned.wav",
        "-af", f"atrim=0:{window_dur:.3f}", "-ar", "48000", "-ac", "1", "/tmp/aligned_trim.wav"
    ])
    run(["mv", "/tmp/aligned_trim.wav", "/tmp/aligned.wav"])

normalize_to_lufs(Path("/tmp/aligned.wav"), SEG_WAV, -23.0)

start_ms = int(round(start_sec * 1000.0))
run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", str(INPUT_MP4), "-i", str(SEG_WAV),
    "-filter_complex",
    f"[0:a]aresample=48000,volume=0.75[bg];[1:a]adelay={start_ms}|{start_ms}[vo];[bg][vo]amix=inputs=2:duration=first:dropout_transition=0[mix]",
    "-map", "[mix]", "-ar", "48000", "-ac", "1", "/tmp/mix.wav"
])

normalize_to_lufs(Path("/tmp/mix.wav"), Path("/tmp/mastered_mix.wav"), -23.0)

run([
    "ffmpeg", "-y", "-loglevel", "error", "-i", str(INPUT_MP4), "-i", "/tmp/mastered_mix.wav",
    "-map", "0:v:0", "-map", "1:a:0",
    "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "1", str(OUTPUT_MP4)
])

placed_end = start_sec + ffprobe_duration(SEG_WAV)
report = {
    "source_language": "en",
    "target_language": lang_code,
    "audio_sample_rate_hz": 48000,
    "audio_channels": 1,
    "measured_lufs": measure_lufs(OUTPUT_MP4),
    "speech_segments": [
        {
            "window_start_sec": start_sec,
            "window_end_sec": end_sec,
            "placed_start_sec": start_sec,
            "placed_end_sec": placed_end,
            "window_duration_sec": window_dur,
            "tts_duration_sec": ffprobe_duration(SEG_WAV),
            "drift_sec": placed_end - end_sec,
            "duration_control": duration_control,
        }
    ],
}
REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
PY
