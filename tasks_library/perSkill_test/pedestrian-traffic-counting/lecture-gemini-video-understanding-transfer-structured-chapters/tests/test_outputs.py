import json
import os
import re


OUTPUT_FILE = os.environ.get("TASK_OUTPUT_FILE", "/app/lecture/chapter_outline.json")
REWARD_FILE = os.environ.get("TASK_REWARD_FILE", "/logs/verifier/reward.txt")
EXPECTED_VIDEO = "session_alpha.avi"
EXPECTED_CHAPTERS = [
    {
        "start_time": "00:00",
        "end_time": "00:12",
        "mode": "讲台讲解",
        "keywords": ["motion", "track"],
    },
    {
        "start_time": "00:12",
        "end_time": "00:24",
        "mode": "白板书写",
        "keywords": ["frame", "differ"],
    },
    {
        "start_time": "00:24",
        "end_time": "00:36",
        "mode": "实物演示",
        "keywords": ["block", "occlusion", "demo"],
    },
    {
        "start_time": "00:36",
        "end_time": "00:48",
        "mode": "问答",
        "keywords": ["light", "shadow", "question"],
    },
]
SUMMARY_GROUPS = [
    ["motion"],
    ["frame", "differ"],
    ["occlusion", "block"],
    ["light", "shadow"],
]
ALLOWED_MODES = {"讲台讲解", "白板书写", "实物演示", "问答"}


def _write_reward(value: float) -> None:
    os.makedirs(os.path.dirname(REWARD_FILE), exist_ok=True)
    with open(REWARD_FILE, "w", encoding="utf-8") as handle:
        handle.write(f"{value:.6f}\n")


def _load_output() -> dict:
    with open(OUTPUT_FILE, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict), "Output must be a JSON object"
    return data


def _validate_top_level(data: dict) -> None:
    assert set(data) == {"video", "overall_summary", "chapters"}, (
        "Top-level keys must be exactly video, overall_summary, chapters"
    )
    assert data["video"] == EXPECTED_VIDEO, f"video must be {EXPECTED_VIDEO!r}"
    assert isinstance(data["overall_summary"], str), "overall_summary must be a string"
    assert data["overall_summary"].strip(), "overall_summary must not be empty"
    assert "\n" not in data["overall_summary"].strip(), "overall_summary must be a single paragraph"
    assert isinstance(data["chapters"], list), "chapters must be a list"


def _validate_chapter_schema(chapter: dict, index: int) -> None:
    assert isinstance(chapter, dict), f"Chapter {index} must be an object"
    assert set(chapter) == {"start_time", "end_time", "title", "mode"}, (
        f"Chapter {index} must contain exactly start_time, end_time, title, mode"
    )
    assert re.fullmatch(r"\d{2}:\d{2}", chapter["start_time"]), (
        f"Chapter {index} start_time must use MM:SS"
    )
    assert re.fullmatch(r"\d{2}:\d{2}", chapter["end_time"]), (
        f"Chapter {index} end_time must use MM:SS"
    )
    assert isinstance(chapter["title"], str) and chapter["title"].strip(), (
        f"Chapter {index} title must be a non-empty string"
    )
    assert chapter["mode"] in ALLOWED_MODES, f"Chapter {index} mode must be one of {sorted(ALLOWED_MODES)}"


def _to_seconds(value: str) -> int:
    minutes, seconds = value.split(":")
    return int(minutes) * 60 + int(seconds)


def test_outputs() -> None:
    if not os.path.exists(OUTPUT_FILE):
        _write_reward(0.0)
        raise AssertionError(f"{OUTPUT_FILE} not found")

    try:
        data = _load_output()
        _validate_top_level(data)

        chapters = data["chapters"]
        assert len(chapters) == len(EXPECTED_CHAPTERS), (
            f"Expected {len(EXPECTED_CHAPTERS)} chapters, got {len(chapters)}"
        )

        previous_end = -1
        total_reward = 0.0

        for idx, (chapter, expected) in enumerate(zip(chapters, EXPECTED_CHAPTERS)):
            _validate_chapter_schema(chapter, idx)
            start_seconds = _to_seconds(chapter["start_time"])
            end_seconds = _to_seconds(chapter["end_time"])
            assert start_seconds < end_seconds, f"Chapter {idx} start_time must be earlier than end_time"
            assert start_seconds >= previous_end, f"Chapter {idx} starts before the previous chapter ends"
            previous_end = end_seconds

            chapter_reward = 0.0
            if chapter["start_time"] == expected["start_time"]:
                chapter_reward += 0.2
            if chapter["end_time"] == expected["end_time"]:
                chapter_reward += 0.2
            if chapter["mode"] == expected["mode"]:
                chapter_reward += 0.3

            title_lower = chapter["title"].lower()
            if any(keyword in title_lower for keyword in expected["keywords"]):
                chapter_reward += 0.3

            total_reward += chapter_reward
            print(
                f"chapter_{idx}: start={chapter['start_time']} end={chapter['end_time']} "
                f"mode={chapter['mode']} reward={chapter_reward:.2f}"
            )

        summary_lower = data["overall_summary"].lower()
        summary_reward = 0.0
        for keyword_group in SUMMARY_GROUPS:
            if any(keyword in summary_lower for keyword in keyword_group):
                summary_reward += 0.05
        total_reward += summary_reward
        print(f"summary_reward={summary_reward:.2f}")

        average_reward = total_reward / (len(EXPECTED_CHAPTERS) + 0.2)
        _write_reward(average_reward)
        print(f"average_reward={average_reward:.6f}")

        assert chapters[0]["start_time"] == "00:00", "The first chapter must start at 00:00"
        assert chapters[-1]["end_time"] == "00:48", "The final chapter must end at 00:48"
        assert average_reward > 0.0, "Reward must be positive for a structurally valid outline"
    except Exception:
        _write_reward(0.0)
        raise
