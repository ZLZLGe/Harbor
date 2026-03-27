import json
import re
import subprocess
import wave
from pathlib import Path

MIX = Path("/outputs/kiosk_mix.wav")
REPORT = Path("/outputs/kiosk_report.json")
SEG = Path("/outputs/tts_segments/seg_0.wav")


def loudness(path: Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        text=True,
        capture_output=True,
        check=False,
    )
    matches = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", proc.stderr)
    return float(matches[-1]) if matches else -70.0


def wav_format(path: Path):
    with wave.open(str(path), "rb") as wav:
        return wav.getframerate(), wav.getnchannels(), wav.getnframes()


def test_outputs_exist():
    assert MIX.exists()
    assert REPORT.exists()
    assert SEG.exists()


def test_audio_formats_are_valid():
    for path in [MIX, SEG]:
        sr, ch, frames = wav_format(path)
        assert sr == 48000
        assert ch == 1
        assert frames > 0


def test_report_and_alignment():
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload["audio_sample_rate_hz"] == 48000
    assert payload["audio_channels"] == 1
    seg = payload["speech_segments"][0]
    assert abs(seg["placed_start_sec"] - seg["window_start_sec"]) < 0.01
    assert abs(seg["drift_sec"]) <= 0.2
    assert seg["duration_control"] in {"rate_adjust", "pad_silence", "trim"}


def test_loudness_target():
    lufs = loudness(MIX)
    assert -25.0 <= lufs <= -21.0
