import json
from pathlib import Path

PRED_FILE = Path("/root/tutorial_index_similar.json")
GT_FILE = Path(__file__).parent / "ground_truth.json"

EXPECTED_TITLES = [
    "What we'll do",
    "How we'll get there",
    "Getting a floor plan",
    "Getting started",
    "Basic Navigation",
    "Import your plan into Blender",
    "Basic transform operations",
    "Setting up the plan and units",
    "It all starts with a plane",
    "Scaling the plane to real dimensions",
    "Getting the plan in place",
    "Tracing the outline",
    "Tracing inner walls",
    "Break",
    "Continue tracing inner walls",
    "Remove doubled vertices",
    "Save",
    "Make the floor",
    "Remove unnecessary geometry",
    "Make the floor's faces",
    "Make the background",
    "Extruding the walls in Z",
    "Reviewing face orientation",
    "Adding thickness to walls with Modifiers",
    "Fixing face orientation errors",
    "Note on face orientation",
    "Save As",
    "If you need thick and thin walls",
    "Great job!",
]


def main() -> None:
    assert PRED_FILE.exists(), f"missing output: {PRED_FILE}"
    pred = json.loads(PRED_FILE.read_text())
    gt = json.loads(GT_FILE.read_text())

    assert set(pred.keys()) == {"video_info", "chapters"}
    assert pred["video_info"]["title"] == "In-Depth Floor Plan Tutorial Part 1"
    assert pred["video_info"]["duration_seconds"] == 1382

    chapters = pred["chapters"]
    assert len(chapters) == 29, f"expected 29 chapters, got {len(chapters)}"

    times = []
    for i, chapter in enumerate(chapters):
        assert "time" in chapter and "title" in chapter, f"chapter {i+1} missing fields"
        assert isinstance(chapter["time"], (int, float))
        assert isinstance(chapter["title"], str)
        assert chapter["title"] == EXPECTED_TITLES[i], f"chapter {i+1} title mismatch"
        times.append(float(chapter["time"]))

    assert times[0] == 0, f"first chapter must start at 0, got {times[0]}"
    for i in range(len(times) - 1):
        assert times[i + 1] > times[i], f"timestamps must be strictly increasing at index {i}"
    assert all(0 <= t <= 1382 for t in times), "timestamps out of video range"

    gt_times = [float(ch["start_time"]) for ch in gt["chapters"]]
    errors = [abs(pt - gt_t) for pt, gt_t in zip(times, gt_times)]
    mae = sum(errors) / len(errors)
    within_10 = sum(1 for e in errors if e <= 10) / len(errors)

    assert mae <= 15.0, f"MAE too high: {mae:.2f}s"
    assert within_10 >= 0.70, f"precision@10 too low: {within_10:.2%}"


if __name__ == "__main__":
    main()
