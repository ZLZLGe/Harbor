import json

INPUT_PATH = "/root/minute_events.json"
OUTPUT_PATH = "/root/transfer1_timeline.json"


def minute_of(ts: str) -> str:
    return ts.split(":", 1)[0].zfill(2)


def build_expected() -> dict:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    out = {"generated_at": "static", "videos": []}
    for video in sorted(payload.get("videos", []), key=lambda item: item["video"]):
        ped_events = [e for e in video.get("events", []) if e.get("actor_type") == "pedestrian"]
        minute_map = {}
        zone_counts = {}
        unique_ids = set()

        for e in ped_events:
            mm = minute_of(e["timestamp"])
            minute_map.setdefault(mm, set()).add(e["track_id"])
            zone_counts[e["zone"]] = zone_counts.get(e["zone"], 0) + 1
            unique_ids.add(e["track_id"])

        peak_minute = min(minute_map.keys(), key=lambda m: (-len(minute_map[m]), m))
        top_zone = min(zone_counts.keys(), key=lambda z: (-zone_counts[z], z))

        out["videos"].append(
            {
                "video": video["video"],
                "peak_minute": peak_minute,
                "unique_pedestrians": len(unique_ids),
                "top_zone": top_zone,
            }
        )

    return out


def test_transfer1_timeline_exact():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        actual = json.load(f)
    assert actual == build_expected()
