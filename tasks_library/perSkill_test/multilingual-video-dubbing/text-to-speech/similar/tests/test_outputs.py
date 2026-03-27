import json
import re
import subprocess
import wave
from pathlib import Path

OUTPUT_VIDEO = Path("/outputs/dubbed.mp4")
REPORT_JSON = Path("/outputs/report.json")
SEG_WAV = Path("/outputs/tts_segments/seg_0.wav")


def ffprobe_audio_info(path: Path):
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    return json.loads(out)["streams"][0]


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


def test_required_files_exist():
    assert OUTPUT_VIDEO.exists(), "missing /outputs/dubbed.mp4"
    assert REPORT_JSON.exists(), "missing /outputs/report.json"
    assert SEG_WAV.exists(), "missing /outputs/tts_segments/seg_0.wav"


def test_seg_wav_format():
    with wave.open(str(SEG_WAV), "rb") as wav:
        assert wav.getframerate() == 48000
        assert wav.getnchannels() == 1
        assert wav.getnframes() > 0


def test_video_audio_format():
    info = ffprobe_audio_info(OUTPUT_VIDEO)
    assert int(info["sample_rate"]) == 48000
    assert int(info["channels"]) == 1


def test_report_schema_and_alignment():
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    assert report["audio_sample_rate_hz"] == 48000
    assert report["audio_channels"] == 1
    assert isinstance(report.get("speech_segments"), list)
    assert report["speech_segments"], "speech_segments cannot be empty"
    seg = report["speech_segments"][0]
    for key in [
        "window_start_sec",
        "window_end_sec",
        "placed_start_sec",
        "placed_end_sec",
        "window_duration_sec",
        "tts_duration_sec",
        "drift_sec",
        "duration_control",
    ]:
        assert key in seg, f"missing key: {key}"
    assert abs(seg["placed_start_sec"] - seg["window_start_sec"]) < 0.01
    assert abs(seg["drift_sec"]) <= 0.2
    assert seg["duration_control"] in {"rate_adjust", "pad_silence", "trim"}


def test_loudness_target():
    measured = measure_lufs(OUTPUT_VIDEO)
    assert -25.0 <= measured <= -21.0, f"unexpected LUFS {measured}"
