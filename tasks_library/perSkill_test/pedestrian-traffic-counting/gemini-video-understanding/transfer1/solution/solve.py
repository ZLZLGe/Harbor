import json

INPUT_PATH = "/root/minute_events.json"
OUTPUT_PATH = "/root/transfer1_timeline.json"


def minute_of(ts: str) -> str:
    return ts.split(":", 1)[0].zfill(2)


def main() -> None:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    output = {"generated_at": "static", "videos": []}

    for video in sorted(payload.get("videos", []), key=lambda item: item["video"]):
        ped_events = [e for e in video.get("events", []) if e.get("actor_type") == "pedestrian"]

        minute_map = {}
        all_ids = set()
        zone_counts = {}

        for e in ped_events:
            minute = minute_of(e["timestamp"])
            minute_map.setdefault(minute, set()).add(e["track_id"])
            all_ids.add(e["track_id"])
            zone = e["zone"]
            zone_counts[zone] = zone_counts.get(zone, 0) + 1

        peak_minute = min(
            minute_map.keys(),
            key=lambda m: (-len(minute_map[m]), m),
        )
        top_zone = min(zone_counts.keys(), key=lambda z: (-zone_counts[z], z))

        output["videos"].append(
            {
                "video": video["video"],
                "peak_minute": peak_minute,
                "unique_pedestrians": len(all_ids),
                "top_zone": top_zone,
            }
        )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
