import json
from pathlib import Path

OUT = Path("/root/similar_chapter_index.json")

EXPECTED = [
    {"time": 0, "title": "What we'll do"},
    {"time": 15, "title": "How we'll get there"},
    {"time": 25, "title": "Getting a floor plan"},
    {"time": 92, "title": "Getting started"},
    {"time": 109, "title": "Basic Navigation"},
    {"time": 126, "title": "Import your plan into Blender"},
    {"time": 169, "title": "Basic transform operations"},
]


def main() -> None:
    assert OUT.exists(), f"missing output file: {OUT}"
    data = json.loads(OUT.read_text(encoding="utf-8"))

    assert data.get("clip_title") == "Floor Plan Tutorial Excerpt A"
    assert data.get("clip_duration_seconds") == 205

    chapters = data.get("chapters")
    assert isinstance(chapters, list), "chapters must be a JSON array"
    assert len(chapters) == len(EXPECTED), f"expected {len(EXPECTED)} chapters, got {len(chapters)}"

    prev = -1
    for got, exp in zip(chapters, EXPECTED):
        assert got.get("title") == exp["title"], f"title mismatch for {exp['title']}"
        time_value = got.get("time")
        assert isinstance(time_value, (int, float)), f"time must be numeric for {exp['title']}"
        assert 0 <= time_value <= 205, f"time out of range for {exp['title']}: {time_value}"
        assert abs(float(time_value) - exp["time"]) <= 4.0, (
            f"time for {exp['title']} is too far from expected: got {time_value}, expected {exp['time']}"
        )
        assert float(time_value) > prev, f"timestamps must be strictly increasing; got {time_value} after {prev}"
        prev = float(time_value)

    assert float(chapters[0]["time"]) == 0.0, "first chapter must start at 0"


if __name__ == "__main__":
    main()
