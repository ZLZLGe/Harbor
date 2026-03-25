#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import wave
from pathlib import Path
import subprocess

INPUT_PATH = Path("/root/review_cards/session.json")
OUTPUT_WAV = Path("/root/review-drill-session.wav")
TIMELINE_PATH = Path("/root/review-drill-timeline.json")
BUILD_DIR = Path("/tmp/review_drill_build")
RESET_SECONDS = 0.75

BUILD_DIR.mkdir(parents=True, exist_ok=True)


def synth_to_wav(text: str, path: Path) -> None:
    subprocess.run(
        [
            "espeak-ng",
            "-s",
            "155",
            "-v",
            "en-us",
            "-w",
            str(path),
            text,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def wav_params(path: Path):
    with wave.open(str(path), "rb") as handle:
        return handle.getparams()


def create_silence(path: Path, duration_seconds: float, nchannels: int, sampwidth: int, framerate: int) -> None:
    frame_count = int(round(duration_seconds * framerate))
    silent_frame = b"\x00" * sampwidth * nchannels
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(nchannels)
        handle.setsampwidth(sampwidth)
        handle.setframerate(framerate)
        handle.writeframes(silent_frame * frame_count)


deck = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
cards = deck["cards"]

timeline_cards = []
segments = []
base_params = None
current_time = 0.0

for index, card in enumerate(cards, start=1):
    question_text = f"Question {index}. {card['prompt']}"
    answer_text = f"Answer {index}. {card['answer']}"

    question_path = BUILD_DIR / f"{index:02d}_question.wav"
    answer_path = BUILD_DIR / f"{index:02d}_answer.wav"
    think_path = BUILD_DIR / f"{index:02d}_think.wav"
    reset_path = BUILD_DIR / f"{index:02d}_reset.wav"

    synth_to_wav(question_text, question_path)
    synth_to_wav(answer_text, answer_path)

    params = wav_params(question_path)
    if base_params is None:
        base_params = params
    if params[:3] != base_params[:3]:
        raise RuntimeError("Question WAV parameters are inconsistent")

    answer_params = wav_params(answer_path)
    if answer_params[:3] != base_params[:3]:
        raise RuntimeError("Answer WAV parameters are inconsistent")

    nchannels = base_params.nchannels
    sampwidth = base_params.sampwidth
    framerate = base_params.framerate

    think_seconds = float(card["think_seconds"])
    create_silence(think_path, think_seconds, nchannels, sampwidth, framerate)
    create_silence(reset_path, RESET_SECONDS, nchannels, sampwidth, framerate)

    question_duration = wav_duration_seconds(question_path)
    think_duration = wav_duration_seconds(think_path)
    answer_duration = wav_duration_seconds(answer_path)
    reset_duration = wav_duration_seconds(reset_path)

    question_start = current_time
    question_end = question_start + question_duration
    think_start = question_end
    think_end = think_start + think_duration
    answer_start = think_end
    answer_end = answer_start + answer_duration
    reset_start = answer_end
    reset_end = reset_start + reset_duration

    timeline_cards.append(
        {
            "card_id": card["card_id"],
            "question_text": question_text,
            "answer_text": answer_text,
            "think_seconds": round(think_duration, 3),
            "reset_seconds": round(reset_duration, 3),
            "question_start_sec": round(question_start, 3),
            "question_end_sec": round(question_end, 3),
            "think_start_sec": round(think_start, 3),
            "think_end_sec": round(think_end, 3),
            "answer_start_sec": round(answer_start, 3),
            "answer_end_sec": round(answer_end, 3),
            "reset_start_sec": round(reset_start, 3),
            "reset_end_sec": round(reset_end, 3),
        }
    )

    segments.extend([question_path, think_path, answer_path, reset_path])
    current_time = reset_end

if base_params is None:
    raise RuntimeError("No cards found in input deck")

with wave.open(str(OUTPUT_WAV), "wb") as out_handle:
    out_handle.setnchannels(base_params.nchannels)
    out_handle.setsampwidth(base_params.sampwidth)
    out_handle.setframerate(base_params.framerate)

    for segment_path in segments:
        with wave.open(str(segment_path), "rb") as in_handle:
            if in_handle.getparams()[:3] != base_params[:3]:
                raise RuntimeError(f"Inconsistent WAV parameters in {segment_path}")
            out_handle.writeframes(in_handle.readframes(in_handle.getnframes()))

TIMELINE_PATH.write_text(
    json.dumps(
        {
            "session_title": deck["session_title"],
            "cards": timeline_cards,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
