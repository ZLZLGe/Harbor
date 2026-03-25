import audioop
import json
import wave
from pathlib import Path


INPUT_PATH = Path("/root/review_cards/session.json")
OUTPUT_WAV = Path("/root/review-drill-session.wav")
TIMELINE_PATH = Path("/root/review-drill-timeline.json")
RESET_SECONDS = 0.75
TIMESTAMP_TOLERANCE = 0.15


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def peak_for_window(path: Path, start_sec: float, end_sec: float) -> int:
    assert end_sec > start_sec, f"Invalid audio window {start_sec} to {end_sec}"
    with wave.open(str(path), "rb") as handle:
        framerate = handle.getframerate()
        start_frame = int(start_sec * framerate)
        frame_count = max(1, int((end_sec - start_sec) * framerate))
        handle.setpos(start_frame)
        frames = handle.readframes(frame_count)
        return int(audioop.max(frames, handle.getsampwidth()))


def narrowed_window(start_sec: float, end_sec: float, trim: float = 0.05):
    if end_sec - start_sec <= trim * 2:
        return start_sec, end_sec
    return start_sec + trim, end_sec - trim


def expected_question_text(index: int, prompt: str) -> str:
    return f"Question {index}. {prompt}"


def expected_answer_text(index: int, answer: str) -> str:
    return f"Answer {index}. {answer}"


def test_outputs_exist():
    assert OUTPUT_WAV.exists(), f"Missing output WAV: {OUTPUT_WAV}"
    assert TIMELINE_PATH.exists(), f"Missing timing map: {TIMELINE_PATH}"


def test_timeline_matches_source_deck_exactly():
    deck = load_json(INPUT_PATH)
    timeline = load_json(TIMELINE_PATH)
    expected_card_keys = {
        "card_id",
        "question_text",
        "answer_text",
        "think_seconds",
        "reset_seconds",
        "question_start_sec",
        "question_end_sec",
        "think_start_sec",
        "think_end_sec",
        "answer_start_sec",
        "answer_end_sec",
        "reset_start_sec",
        "reset_end_sec",
    }

    assert set(timeline.keys()) == {"session_title", "cards"}
    assert timeline["session_title"] == deck["session_title"]
    assert isinstance(timeline["cards"], list)
    assert len(timeline["cards"]) == len(deck["cards"]) == 5

    previous_end = -1.0
    for index, (source_card, observed) in enumerate(zip(deck["cards"], timeline["cards"]), start=1):
        assert set(observed.keys()) == expected_card_keys
        assert observed["card_id"] == source_card["card_id"]
        assert observed["question_text"] == expected_question_text(index, source_card["prompt"])
        assert observed["answer_text"] == expected_answer_text(index, source_card["answer"])
        assert abs(float(observed["think_seconds"]) - float(source_card["think_seconds"])) <= 0.05
        assert abs(float(observed["reset_seconds"]) - RESET_SECONDS) <= 0.05

        timestamps = [
            float(observed["question_start_sec"]),
            float(observed["question_end_sec"]),
            float(observed["think_start_sec"]),
            float(observed["think_end_sec"]),
            float(observed["answer_start_sec"]),
            float(observed["answer_end_sec"]),
            float(observed["reset_start_sec"]),
            float(observed["reset_end_sec"]),
        ]

        assert timestamps == sorted(timestamps), f"Timestamps are not nondecreasing for {source_card['card_id']}"
        assert timestamps[0] >= previous_end - 0.001
        previous_end = timestamps[-1]

        assert abs(observed["question_end_sec"] - observed["think_start_sec"]) <= 0.01
        assert abs(observed["think_end_sec"] - observed["answer_start_sec"]) <= 0.01
        assert abs(observed["answer_end_sec"] - observed["reset_start_sec"]) <= 0.01


def test_wav_is_pcm_and_duration_matches_timeline():
    timeline = load_json(TIMELINE_PATH)

    with wave.open(str(OUTPUT_WAV), "rb") as handle:
        assert handle.getnchannels() in (1, 2), "WAV must be mono or stereo"
        assert handle.getsampwidth() in (1, 2, 4), "Unexpected PCM sample width"
        assert handle.getframerate() >= 16000, "Sample rate is too low for speech"

    duration = wav_duration_seconds(OUTPUT_WAV)
    expected_duration = float(timeline["cards"][-1]["reset_end_sec"])

    assert abs(duration - expected_duration) <= TIMESTAMP_TOLERANCE, (
        f"WAV duration {duration:.3f}s does not match timeline end {expected_duration:.3f}s"
    )


def test_declared_pause_windows_are_silent():
    timeline = load_json(TIMELINE_PATH)

    for card in timeline["cards"]:
        think_start, think_end = narrowed_window(float(card["think_start_sec"]), float(card["think_end_sec"]))
        reset_start, reset_end = narrowed_window(float(card["reset_start_sec"]), float(card["reset_end_sec"]))

        think_peak = peak_for_window(OUTPUT_WAV, think_start, think_end)
        reset_peak = peak_for_window(OUTPUT_WAV, reset_start, reset_end)

        assert think_peak == 0, f"Think gap for {card['card_id']} is not fully silent"
        assert reset_peak == 0, f"Reset gap for {card['card_id']} is not fully silent"


def test_declared_spoken_windows_contain_audio():
    timeline = load_json(TIMELINE_PATH)

    for card in timeline["cards"]:
        question_start, question_end = narrowed_window(
            float(card["question_start_sec"]),
            float(card["question_end_sec"]),
        )
        answer_start, answer_end = narrowed_window(
            float(card["answer_start_sec"]),
            float(card["answer_end_sec"]),
        )

        question_peak = peak_for_window(OUTPUT_WAV, question_start, question_end)
        answer_peak = peak_for_window(OUTPUT_WAV, answer_start, answer_end)

        assert question_peak > 0, f"Question span for {card['card_id']} appears silent"
        assert answer_peak > 0, f"Answer span for {card['card_id']} appears silent"
