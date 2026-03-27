import json
import re
import subprocess
import wave
from pathlib import Path

MANIFEST = Path("/outputs/prompt_manifest.json")


def loudness(path: Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        text=True,
        capture_output=True,
        check=False,
    )
    matches = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", proc.stderr)
    return float(matches[-1]) if matches else -70.0


def wav_info(path: Path):
    with wave.open(str(path), "rb") as wav:
        return wav.getframerate(), wav.getnchannels(), wav.getnframes()


def test_manifest_exists_and_schema():
    assert MANIFEST.exists(), "missing prompt_manifest.json"
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["audio_sample_rate_hz"] == 48000
    assert payload["audio_channels"] == 1
    assert isinstance(payload.get("items"), list)
    assert len(payload["items"]) == 3


def test_each_prompt_file_meets_constraints():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in payload["items"]:
        for key in ["id", "file", "target_duration_sec", "actual_duration_sec", "drift_sec", "duration_control", "lufs"]:
            assert key in item, f"missing {key}"
        wav_path = Path(item["file"])
        assert wav_path.exists(), f"missing {wav_path}"
        sr, ch, frames = wav_info(wav_path)
        assert sr == 48000
        assert ch == 1
        assert frames > 0
        assert abs(float(item["drift_sec"])) <= 0.2
        assert item["duration_control"] in {"rate_adjust", "pad_silence", "trim"}
        measured = loudness(wav_path)
        assert -25.0 <= measured <= -21.0
